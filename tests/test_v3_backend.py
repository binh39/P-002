from __future__ import annotations

import json
from collections.abc import Generator
from pathlib import Path
from types import SimpleNamespace

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
from src.optimization.models import SymbolTarget
from src.optimization.prompts import PromptBundle
from src.services.experiments import execute_experiment


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
        "baseline_prompt": "eval/prompt_optimization/prompts/gpt_v2_baseline.json",
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


def test_ui_experiment_compares_coverup_bundle_with_gepa(
    database,
    monkeypatch,
):
    with database() as session:
        experiment = create_experiment(
            session,
            ExperimentCreate.model_validate(experiment_payload()),
        )
        experiment_id = experiment.id

    baseline = PromptBundle.load(
        Path("eval/prompt_optimization/prompts/gpt_v2_baseline.json")
    )
    optimized_bundle = PromptBundle(
        initial=baseline.initial + "\nPrefer boundary cases.",
        error=baseline.error,
        missing_coverage=baseline.missing_coverage,
    )
    target = SymbolTarget("isort", "isort/api.py", "sort_file", "validation")
    captured = {}

    monkeypatch.setattr("src.services.experiments.SessionLocal", database)
    monkeypatch.setattr(
        "src.services.experiments.resolve_model_provider",
        lambda: SimpleNamespace(
            generation_model="openai/gpt-4o-mini",
            optimization_model="openai/gpt-4o-mini",
        ),
    )
    monkeypatch.setattr("src.services.experiments.dspy.LM", lambda *a, **k: object())
    monkeypatch.setattr("src.services.experiments.PromptBundle.save", lambda *a: None)
    monkeypatch.setattr(
        "src.services.experiments.load_targets",
        lambda path, split: [
            SymbolTarget("isort", "isort/api.py", "sort_file", split)
        ],
    )

    def fake_optimize(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(best_bundle=optimized_bundle)

    def fake_evaluate(runner, targets, bundle, *args, **kwargs):
        score = 0.4 if bundle == baseline else 0.8
        return {
            "aggregate": {
                "score": score,
                "statement_coverage": score,
                "branch_coverage": score,
            },
            "results": [
                {
                    "target": target.__dict__,
                    "coverage": {"valid": True},
                    "score": score,
                }
            ],
        }

    monkeypatch.setattr("src.services.experiments.optimize", fake_optimize)
    monkeypatch.setattr(
        "src.services.experiments.evaluate_bundle_repeated", fake_evaluate
    )

    execute_experiment(experiment_id)

    assert captured["baseline"] == baseline
    assert captured["max_metric_calls"] == 300
    assert "max_iterations" not in captured
    with database() as session:
        stored = session.get(type(experiment), experiment_id)
        assert stored.status == PromptStatus.IN_REVIEW
        candidates = list(stored.candidates)
        assert len(candidates) == 2
        payloads = [json.loads(candidate.prompt_text) for candidate in candidates]
        assert [payload["strategy"] for payload in payloads] == ["coverup", "gepa"]
        assert [candidate.fitness_score for candidate in candidates] == [0.4, 0.8]


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
                fitness_score=0.4,
                latency_seconds=10.0,
            ),
        )
        best = create_candidate(
            session,
            experiment.id,
            CandidateCreate(
                prompt_text="frontier",
                fitness_score=0.8,
                latency_seconds=5.0,
            ),
        )

    response = await client.get(f"/api/v1/experiments/{experiment.id}/pareto")

    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [best.id]


def test_pareto_keeps_tradeoff_points():
    candidates = [
        {"id": "fast", "coverage": 0.6, "latency": 0.1},
        {"id": "strong", "coverage": 0.9, "latency": 1.0},
        {"id": "dominated", "coverage": 0.5, "latency": 1.5},
    ]

    frontier = compute_pareto_frontier(
        candidates,
        maximize=["coverage"],
        minimize=["latency"],
    )

    assert {candidate["id"] for candidate in frontier} == {"fast", "strong"}


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
    assert "Branch coverage" in explanation
    assert "Mutation" not in explanation
