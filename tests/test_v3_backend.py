from __future__ import annotations

from collections.abc import Generator

import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from analytics.explanation import generate_explanation
from analytics.pareto import compute_pareto_frontier
from db.base import Base, get_session
from db.crud import create_candidate, create_experiment
from db.models import PromptStatus
from db.schemas import CandidateCreate, ExperimentCreate
from harness.models import HarnessResult
from src.main import app


@pytest_asyncio.fixture
async def database(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'v3.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)

    def override() -> Generator[Session, None, None]:
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_session] = override
    try:
        yield testing_session
    finally:
        app.dependency_overrides.pop(get_session, None)
        Base.metadata.drop_all(engine)
        engine.dispose()


def experiment_payload():
    return {
        "name": "isort optimization",
        "baseline_prompt": "Write focused pytest tests.",
        "module_path": "src/sample_repo/isort/isort",
        "dataset_path": "eval/prompt_optimization/datasets/isort_symbols.jsonl",
        "source_root": "src/sample_repo/isort",
        "budget_limit": 2.0,
    }


@pytest.mark.asyncio
async def test_experiment_api_create_list_and_schedule(
    client,
    database,
    monkeypatch,
):
    scheduled = []
    monkeypatch.setattr(
        "src.api.experiments.execute_experiment",
        lambda experiment_id: scheduled.append(experiment_id),
    )

    created = await client.post("/api/v1/experiments", json=experiment_payload())
    assert created.status_code == 201
    experiment = created.json()
    assert experiment["status"] == "DRAFT"

    listed = await client.get("/api/v1/experiments")
    assert listed.status_code == 200
    assert [row["id"] for row in listed.json()] == [experiment["id"]]

    run = await client.post(f"/api/v1/experiments/{experiment['id']}/run")
    assert run.status_code == 202
    assert scheduled == [experiment["id"]]


@pytest.mark.asyncio
async def test_candidate_approval_is_persisted_once(client, database):
    with database() as session:
        experiment = create_experiment(
            session,
            ExperimentCreate.model_validate(experiment_payload()),
        )
        candidate = create_candidate(
            session,
            experiment.id,
            CandidateCreate(
                prompt_text="candidate",
                fitness_score=0.7,
                mutation_score=0.6,
            ),
        )
        candidate_id = candidate.id

    approved = await client.post(
        f"/api/v1/candidates/{candidate_id}/approve",
        json={"reviewer_id": "reviewer@example.com", "comment": "Looks good"},
    )
    assert approved.status_code == 200
    assert approved.json()["decision"] == "approved"

    duplicate = await client.post(
        f"/api/v1/candidates/{candidate_id}/approve",
        json={"reviewer_id": "reviewer@example.com"},
    )
    assert duplicate.status_code == 409

    with database() as session:
        assert session.get(type(experiment), experiment.id).status == PromptStatus.APPROVED


@pytest.mark.asyncio
async def test_pareto_endpoint_returns_only_nondominated_candidates(client, database):
    with database() as session:
        experiment = create_experiment(
            session,
            ExperimentCreate.model_validate(experiment_payload()),
        )
        create_candidate(
            session,
            experiment.id,
            CandidateCreate(
                prompt_text="dominated",
                mutation_score=0.4,
                cost_usd=1.0,
            ),
        )
        best = create_candidate(
            session,
            experiment.id,
            CandidateCreate(
                prompt_text="frontier",
                mutation_score=0.8,
                cost_usd=0.5,
            ),
        )

    response = await client.get(f"/api/v1/experiments/{experiment.id}/pareto")

    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [best.id]


def test_pareto_keeps_tradeoff_points():
    candidates = [
        {"id": "cheap", "mutation": 0.6, "cost": 0.1},
        {"id": "strong", "mutation": 0.9, "cost": 1.0},
        {"id": "dominated", "mutation": 0.5, "cost": 1.5},
    ]

    frontier = compute_pareto_frontier(
        candidates,
        maximize=["mutation"],
        minimize=["cost"],
    )

    assert {candidate["id"] for candidate in frontier} == {"cheap", "strong"}


def test_explanation_calls_out_measured_regression():
    baseline = HarnessResult(
        build_ok=True,
        build_error="",
        num_tests=2,
        num_passed=2,
        pass_rate=1.0,
        statement_coverage=0.7,
        branch_coverage=0.6,
        mutation_score=0.5,
        surviving_mutant_lines=[10],
    )
    candidate = HarnessResult(
        build_ok=True,
        build_error="",
        num_tests=2,
        num_passed=1,
        pass_rate=0.5,
        statement_coverage=0.8,
        branch_coverage=0.7,
        mutation_score=0.4,
        surviving_mutant_lines=[10, 20],
    )

    explanation = generate_explanation(baseline, candidate)

    assert "Pass rate: 100% → 50% (-50%)" in explanation
    assert "Regression—new surviving mutant lines: [20]" in explanation
