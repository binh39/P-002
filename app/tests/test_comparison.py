import json
from datetime import UTC, datetime

import pytest

from backend.core.errors import AppError
from backend.modules.experiments.dispatcher import InlineComparisonDispatcher
from backend.modules.experiments.prompts import PromptBundle, baseline_prompt
from backend.modules.experiments.repository import InMemoryExperimentRepository
from backend.modules.experiments.schemas import (
    ExperimentRecord,
    ExperimentStatus,
    OptimizationRunRecord,
    PromptRole,
    PromptSnapshotOrigin,
    PromptVersionStatus,
)
from backend.modules.experiments.service import ExperimentService


class FakeStorage:
    def __init__(self):
        self.objects = {}

    async def write(self, object_name, content, content_type):
        self.objects[object_name] = (content, content_type)


def candidate_prompt() -> PromptBundle:
    prompt = baseline_prompt()
    return PromptBundle(initial=prompt.initial + "\nPrefer boundary cases.", error=prompt.error)


@pytest.mark.asyncio
async def test_cloud_final_validation_creates_reviewable_version_and_review_is_idempotent():
    repository = InMemoryExperimentRepository()
    now = datetime.now(UTC)
    baseline = baseline_prompt()
    candidate = candidate_prompt()
    experiment = ExperimentRecord(
        id="experiment-1",
        owner_id="owner-1",
        project_id="project-1",
        name="Locked comparison",
        target_function_ids=["train_fn", "validation_fn", "test_fn"],
        dataset_splits={"train": ["train_fn"], "validation": ["validation_fn"], "test": ["test_fn"]},
        optimization_eligible=True,
        status=ExperimentStatus.OPTIMIZATION_SUCCEEDED,
        optimization_run_id="optimization-1",
        created_at=now,
        updated_at=now,
    )
    await repository.create(experiment)
    await repository.create_optimization_run(
        OptimizationRunRecord(
            id="optimization-1",
            experiment_id=experiment.id,
            status=ExperimentStatus.OPTIMIZATION_SUCCEEDED,
            parent_prompt_digest=baseline.digest(),
            candidate_prompt=candidate.as_candidate(),
            candidate_prompt_digest=candidate.digest(),
            final_validation={
                "promoted": True,
                "absolute_gain": 0.4,
                "baseline_aggregate_coverage": {"score": 0.4, "statement_coverage": 0.4, "branch_coverage": 0.4},
                "optimized_aggregate_coverage": {"score": 0.8, "statement_coverage": 0.8, "branch_coverage": 0.8},
            },
            created_at=now,
            finished_at=now,
        )
    )
    storage = FakeStorage()
    service = ExperimentService(repository, object(), object(), storage)
    service.set_comparison_dispatcher(InlineComparisonDispatcher(service.execute_comparison))

    comparison = await service.request_comparison(experiment.id, experiment.owner_id)

    assert comparison.status == ExperimentStatus.IN_REVIEW
    assert comparison.promotion_eligible is True
    assert comparison.prompt_version_id
    baseline_snapshot = await repository.get_prompt_snapshot(experiment.id, PromptRole.BASELINE)
    optimized_snapshot = await repository.get_prompt_snapshot(experiment.id, PromptRole.OPTIMIZED)
    assert baseline_snapshot is not None
    assert optimized_snapshot is not None
    assert baseline_snapshot.prompt_digest == baseline.digest()
    assert optimized_snapshot.prompt_digest == candidate.digest()
    assert optimized_snapshot.origin == PromptSnapshotOrigin.OPTIMIZED_CANDIDATE
    artifact = json.loads(storage.objects[comparison.artifact_objects["final_validation.json"]][0])
    assert artifact["promoted"] is True
    approved = await service.review_prompt_version(
        comparison.prompt_version_id, experiment.owner_id, PromptVersionStatus.APPROVED, "Coverage improved"
    )
    approved_again = await service.review_prompt_version(
        comparison.prompt_version_id, experiment.owner_id, PromptVersionStatus.APPROVED, "ignored retry"
    )
    assert approved_again.reviewed_at == approved.reviewed_at
    with pytest.raises(AppError):
        await service.review_prompt_version(
            comparison.prompt_version_id, experiment.owner_id, PromptVersionStatus.REJECTED, "changed mind"
        )


@pytest.mark.asyncio
async def test_prompt_registry_keeps_baseline_as_final_prompt_when_candidate_loses():
    repository = InMemoryExperimentRepository()
    now = datetime.now(UTC)
    baseline = baseline_prompt()
    candidate = candidate_prompt()
    experiment = ExperimentRecord(
        id="retained-baseline-experiment",
        owner_id="owner-1",
        project_id="project-1",
        name="Baseline retention",
        target_function_ids=["train_fn", "validation_fn", "test_fn"],
        dataset_splits={"train": ["train_fn"], "validation": ["validation_fn"], "test": ["test_fn"]},
        optimization_eligible=True,
        status=ExperimentStatus.OPTIMIZATION_SUCCEEDED,
        optimization_run_id="retained-baseline-optimization",
        baseline_prompt=baseline.as_candidate(),
        created_at=now,
        updated_at=now,
    )
    await repository.create(experiment)
    await repository.create_optimization_run(
        OptimizationRunRecord(
            id="retained-baseline-optimization",
            experiment_id=experiment.id,
            status=ExperimentStatus.OPTIMIZATION_SUCCEEDED,
            parent_prompt_digest=baseline.digest(),
            candidate_prompt=candidate.as_candidate(),
            candidate_prompt_digest=candidate.digest(),
            final_validation={
                "promoted": False,
                "absolute_gain": -0.1,
                "baseline_aggregate_coverage": {"score": 0.8},
                "optimized_aggregate_coverage": {"score": 0.7},
            },
            created_at=now,
            finished_at=now,
        )
    )
    service = ExperimentService(repository, object(), object(), FakeStorage())
    service.set_comparison_dispatcher(InlineComparisonDispatcher(service.execute_comparison))

    await service.request_comparison(experiment.id, experiment.owner_id)
    entry = await service.get_prompt_registry_entry(experiment.id, experiment.owner_id)

    assert entry.optimized is not None
    assert entry.optimized.origin == PromptSnapshotOrigin.BASELINE_RETAINED
    assert entry.optimized.prompt_digest == baseline.digest()
    assert entry.baseline_metrics.score == 0.8
    assert entry.optimized_metrics.score == 0.8
