import json
from datetime import UTC, datetime

import pytest

from src.core.errors import AppError
from src.modules.experiments.dispatcher import InlineComparisonDispatcher
from src.modules.experiments.prompts import PromptBundle, baseline_prompt
from src.modules.experiments.repository import InMemoryExperimentRepository
from src.modules.experiments.schemas import (
    ExperimentRecord,
    ExperimentStatus,
    OptimizationRunRecord,
    PromptVersionStatus,
)
from src.modules.experiments.service import ExperimentService


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
