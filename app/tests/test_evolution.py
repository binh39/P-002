from datetime import UTC, datetime, timedelta

import pytest

from backend.modules.experiments.evolution import CloudLogLine, parse_evolution_log
from backend.modules.experiments.repository import InMemoryExperimentRepository
from backend.modules.experiments.schemas import (
    EvolutionIteration,
    EvolutionMetricPoint,
    EvolutionResponse,
    ExperimentRecord,
    ExperimentStatus,
    OptimizationRunRecord,
)
from backend.modules.experiments.service import ExperimentService


class MemoryStorage:
    def __init__(self):
        self.objects = {}

    async def read(self, name):
        return self.objects[name][0]

    async def write(self, name, content, content_type):
        self.objects[name] = (content, content_type)


def evolution_result():
    return EvolutionResponse(
        available=True,
        message="Parsed from Cloud Run stdout.",
        iterations=[
            EvolutionIteration(
                iteration=0,
                strategy="baseline",
                parent_program="Program 0",
                parent_validation_score=0.25,
                decision="Baseline evaluated",
                best_score=0.25,
            )
        ],
        metrics=[EvolutionMetricPoint(iteration=0, score=0.25)],
    )


def test_parses_reflective_mutation_and_carries_best_candidate_metrics_forward():
    started = datetime(2026, 8, 10, tzinfo=UTC)
    messages = [
        "Iteration 0: Baseline validation aggregate metrics: {'score': 0.259945, 'statement': 0.31, 'branch': 0.2385}",
        "Iteration 0: Base program full valset score: 0.259945 over 10 / 10 examples",
        "Iteration 1: Selected program 0 score: 0.259945",
        "Iteration 1: Proposed new text for initial: You are an expert Python developer.",
        "Inspect exact signatures and branch predicates.",
        "Iteration 1: New subsample score 1.2237 is better than old score 1.0435. Continue to full eval and add to candidate pool.",
        "Iteration 1: Val aggregate for new program: 0.831",
        "Iteration 1: Objective aggregate scores for new program: {'statement_coverage': 0.81, 'branch_coverage': 0.84}",
        "Iteration 1: Objective pareto front scores: {'statement': 0.99, 'branch': 0.98}",
        "Iteration 1: Valset pareto front aggregate score: 0.985",
        "Iteration 1: Best program as per aggregate score on valset: 1",
        "Iteration 1: Best score on valset: 0.831",
        "Iteration 1: New program candidate index: 1",
        "Iteration 2: Selected program 1 score: 0.8319",
        "Iteration 2: Proposed new text for error: Repair the failing test.",
        "Iteration 2: New subsample score 0.9398 is not better than old score 0.9625, skipping",
    ]
    entries = [
        CloudLogLine(timestamp=started + timedelta(seconds=index), text=message)
        for index, message in enumerate(messages)
    ]

    result = parse_evolution_log(entries)

    assert result.available is True
    assert [item.iteration for item in result.iterations] == [0, 1, 2]
    baseline = result.iterations[0]
    assert baseline.best_statement == 0.31
    assert baseline.best_branch == 0.2385
    assert baseline.best_score == 0.259945
    first = result.iterations[1]
    assert first.strategy == "reflective mutation"
    assert first.parent_program == "Program 0"
    assert first.component == "initial"
    assert first.proposed_prompt == (
        "You are an expert Python developer.\nInspect exact signatures and branch predicates."
    )
    assert first.parent_minibatch_sum == 1.0435
    assert first.candidate_minibatch_sum == 1.2237
    assert first.decision == "Accepted"
    assert first.best_statement == 0.81
    assert first.best_branch == 0.84
    assert first.best_score == 0.831
    assert first.best_candidate_changed is True

    second = result.iterations[2]
    assert second.decision == "Rejected"
    assert second.best_candidate_changed is False
    assert second.pareto_changed is False
    assert second.best_statement == first.best_statement
    assert second.best_branch == first.best_branch
    assert second.best_score == first.best_score


def test_full_validation_candidate_does_not_replace_metrics_when_not_best():
    messages = [
        "Iteration 0: Baseline validation aggregate metrics: {'score': 0.9, 'statement': 0.8, 'branch': 0.942857}",
        "Iteration 0: Base program full valset score: 0.9 over 2 / 2 examples",
        "Iteration 1: Selected program 0 score: 0.9",
        "Iteration 1: New subsample score 1.1 is better than old score 1.0. Continue to full eval and add to candidate pool.",
        "Iteration 1: Val aggregate for new program: 0.76",
        "Iteration 1: Objective aggregate scores for new program: {'statement_coverage': 0.2, 'branch_coverage': 1.0}",
        "Iteration 1: Best program as per aggregate score on valset: 0",
        "Iteration 1: Best score on valset: 0.9",
        "Iteration 1: New program candidate index: 1",
    ]

    result = parse_evolution_log([CloudLogLine(timestamp=None, text=message) for message in messages])

    candidate = result.iterations[1]
    assert candidate.decision == "Accepted"
    assert candidate.best_candidate_changed is False
    assert candidate.best_score == 0.9
    assert candidate.best_statement == 0.8
    assert candidate.best_branch == 0.942857
    assert result.metrics[1].score == 0.9


def test_legacy_macro_objectives_are_not_shown_as_micro_coverage():
    messages = [
        "Iteration 0: Baseline validation aggregate metrics: {'score': 0.5, 'statement': 0.5, 'branch': 0.5}",
        "Iteration 0: Base program full valset score: 0.5 over 2 / 2 examples",
        "Iteration 1: Val aggregate for new program: 0.8",
        "Iteration 1: Objective aggregate scores for new program: {'statement': 0.9, 'branch': 0.9}",
        "Iteration 1: Best program as per aggregate score on valset: 1",
        "Iteration 1: Best score on valset: 0.8",
        "Iteration 1: New program candidate index: 1",
    ]

    result = parse_evolution_log([CloudLogLine(timestamp=None, text=message) for message in messages])

    candidate = result.iterations[1]
    assert candidate.best_statement is None
    assert candidate.best_branch is None
    assert candidate.best_score == 0.8


def test_returns_waiting_state_before_iteration_logs_arrive():
    result = parse_evolution_log([])

    assert result.available is False
    assert result.iterations == []
    assert "not published" in result.message


@pytest.mark.asyncio
async def test_completed_run_backfills_and_reuses_evolution_snapshot():
    repository = InMemoryExperimentRepository()
    storage = MemoryStorage()
    now = datetime.now(UTC)
    experiment = ExperimentRecord(
        id="experiment-1",
        owner_id="owner-1",
        project_id="project-1",
        name="GEPA history",
        status=ExperimentStatus.OPTIMIZATION_SUCCEEDED,
        created_at=now,
        updated_at=now,
    )
    run = OptimizationRunRecord(
        id="run-1",
        experiment_id=experiment.id,
        status=ExperimentStatus.OPTIMIZATION_SUCCEEDED,
        parent_prompt_digest="parent",
        cloud_artifact_prefix="runner-jobs/gepa/a1b2c3/artifacts",
        created_at=now,
        started_at=now,
        finished_at=now,
    )
    await repository.create(experiment)
    await repository.create_optimization_run(run)

    class CloudEvolution:
        calls = 0

        async def evolution(self, *args, **kwargs):
            self.calls += 1
            return evolution_result()

    cloud = CloudEvolution()
    service = ExperimentService(repository, object(), object(), storage, cloud_optimizer=cloud)

    first = await service.get_optimization_evolution(run.id, experiment.owner_id)
    stored = await repository.get_optimization_run(run.id)
    snapshot = stored.artifact_objects["evolution.json"]
    second = await service.get_optimization_evolution(run.id, experiment.owner_id)

    assert first == second == evolution_result()
    assert cloud.calls == 1
    assert snapshot in storage.objects


@pytest.mark.asyncio
async def test_cancelled_run_stops_cloud_execution_and_preserves_history():
    repository = InMemoryExperimentRepository()
    storage = MemoryStorage()
    now = datetime.now(UTC)
    experiment = ExperimentRecord(
        id="experiment-cancel",
        owner_id="owner-1",
        project_id="project-1",
        name="Cancelable GEPA",
        status=ExperimentStatus.OPTIMIZING,
        optimization_run_id="run-cancel",
        created_at=now,
        updated_at=now,
    )
    run = OptimizationRunRecord(
        id="run-cancel",
        experiment_id=experiment.id,
        status=ExperimentStatus.OPTIMIZING,
        parent_prompt_digest="parent",
        cloud_artifact_prefix="runner-jobs/gepa/cancel123/artifacts",
        created_at=now,
        started_at=now,
    )
    await repository.create(experiment)
    await repository.create_optimization_run(run)

    class CancellableCloud:
        cancelled = False

        async def cancel(self, *args, **kwargs):
            self.cancelled = True

        async def evolution(self, *args, **kwargs):
            return evolution_result()

    cloud = CancellableCloud()
    service = ExperimentService(repository, object(), object(), storage, cloud_optimizer=cloud)

    response = await service.cancel_optimization(run.id, experiment.owner_id)
    stored_experiment = await repository.get(experiment.id)

    assert cloud.cancelled is True
    assert response.status == ExperimentStatus.CANCELLED
    assert stored_experiment.status == ExperimentStatus.CANCELLED
    assert "evolution.json" in response.artifact_objects
