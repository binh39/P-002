import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from src.core.errors import AppError
from src.modules.experiments.comparison import compare_prompts
from src.modules.experiments.dispatcher import InlineComparisonDispatcher
from src.modules.experiments.executor import BaselineExecution
from src.modules.experiments.optimizer import OptimizationTarget
from src.modules.experiments.prompts import PromptBundle, baseline_prompt
from src.modules.experiments.repository import InMemoryExperimentRepository
from src.modules.experiments.schemas import (
    ExperimentRecord,
    ExperimentStatus,
    OptimizationRunRecord,
    PromptVersionStatus,
)
from src.modules.experiments.service import ExperimentService


class ComparisonExecutor:
    def __init__(self, flaky=False):
        self.calls = 0
        self.flaky = flaky

    async def execute(self, archive, source_directory, symbols, prompt):
        del archive, source_directory
        self.calls += 1
        candidate = "Prefer boundary cases." in prompt.initial
        score = 0.8 if candidate else 0.4
        if candidate and self.flaky and self.calls % 2:
            score = 0.6
        symbol = symbols[0]
        metric = {
            "valid": True,
            "covered_statements": int(score * 10),
            "num_statements": 10,
            "covered_branches": int(score * 10),
            "num_branches": 10,
            "statement_coverage": score,
            "branch_coverage": score,
            "score": score,
        }
        return BaselineExecution(score, score, score, {}, {symbol: metric})


def candidate_prompt() -> PromptBundle:
    prompt = baseline_prompt()
    return PromptBundle(initial=prompt.initial + "\nPrefer boundary cases.", error=prompt.error)


@pytest.mark.asyncio
async def test_paired_comparison_uses_same_targets_and_replicates():
    executor = ComparisonExecutor()
    targets = [
        OptimizationTarget(id="fn-1", symbol="pkg.one", source="def one(): pass", split="test"),
        OptimizationTarget(id="fn-2", symbol="pkg.two", source="def two(): pass", split="test"),
    ]

    result = await compare_prompts(
        executor=executor,
        archive=b"archive",
        source_directory="src",
        targets=targets,
        baseline=baseline_prompt(),
        candidate=candidate_prompt(),
        replicates=2,
    )

    assert executor.calls == 8
    assert result.baseline["score"] == pytest.approx(0.4)
    assert result.candidate["score"] == pytest.approx(0.8)
    assert result.absolute_gain == pytest.approx(0.4)
    assert result.relative_gain == pytest.approx(1.0)
    assert result.promotion_eligible is True
    assert all(delta["score"] == pytest.approx(0.4) for delta in result.paired_deltas)


@pytest.mark.asyncio
async def test_flaky_candidate_is_blocked_by_hard_gate():
    target = OptimizationTarget(id="fn-1", symbol="pkg.one", source="source", split="test")

    result = await compare_prompts(
        executor=ComparisonExecutor(flaky=True),
        archive=b"archive",
        source_directory="src",
        targets=[target],
        baseline=baseline_prompt(),
        candidate=candidate_prompt(),
        replicates=2,
    )

    assert result.absolute_gain > 0
    assert result.promotion_eligible is False
    assert result.candidate["flaky_targets"] == ["fn-1"]


@pytest.mark.asyncio
async def test_identical_candidate_skips_costly_final_evaluation():
    executor = ComparisonExecutor()
    target = OptimizationTarget(id="fn-1", symbol="pkg.one", source="source", split="test")

    result = await compare_prompts(
        executor=executor,
        archive=b"archive",
        source_directory="src",
        targets=[target],
        baseline=baseline_prompt(),
        candidate=baseline_prompt(),
        replicates=2,
    )

    assert executor.calls == 0
    assert result.promotion_eligible is False
    assert "identical" in result.decision_reason


class FakeProjects:
    async def require_owned(self, project_id, owner_id):
        return SimpleNamespace(
            id=project_id,
            owner_id=owner_id,
            object_name="sources/project.zip",
            settings=SimpleNamespace(runtime=SimpleNamespace(source_directory="src")),
        )


class FakeFunctions:
    async def get(self, project_id, function_id):
        del project_id
        return SimpleNamespace(id=function_id, qualified_name=f"pkg.{function_id}", source="source")


class FakeStorage:
    def __init__(self):
        self.objects = {}

    async def read(self, object_name):
        assert object_name == "sources/project.zip"
        return b"archive"

    async def write(self, object_name, content, content_type):
        self.objects[object_name] = (content, content_type)


@pytest.mark.asyncio
async def test_comparison_creates_reviewable_version_and_review_is_idempotent():
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
            created_at=now,
            finished_at=now,
        )
    )
    storage = FakeStorage()
    service = ExperimentService(
        repository,
        FakeProjects(),
        FakeFunctions(),
        storage,
        ComparisonExecutor(),
        final_evaluation_replicates=2,
    )
    service.set_comparison_dispatcher(InlineComparisonDispatcher(service.execute_comparison))

    comparison = await service.request_comparison(experiment.id, experiment.owner_id)

    assert comparison.status == ExperimentStatus.IN_REVIEW
    assert comparison.promotion_eligible is True
    assert comparison.prompt_version_id
    assert set(comparison.artifact_objects) == {"final_validation.json"}
    artifact = json.loads(storage.objects[comparison.artifact_objects["final_validation.json"]][0])
    assert artifact["protocol_version"] == 1
    assert artifact["test_target_ids"] == ["test_fn"]
    assert artifact["candidate_prompt_digest"] == candidate.digest()

    approved = await service.review_prompt_version(
        comparison.prompt_version_id, experiment.owner_id, PromptVersionStatus.APPROVED, "Coverage improved"
    )
    approved_again = await service.review_prompt_version(
        comparison.prompt_version_id, experiment.owner_id, PromptVersionStatus.APPROVED, "ignored retry"
    )
    assert approved.status == PromptVersionStatus.APPROVED
    assert approved_again.reviewed_at == approved.reviewed_at
    assert approved_again.review_comment == "Coverage improved"
    assert (await repository.get(experiment.id)).status == ExperimentStatus.APPROVED

    with pytest.raises(AppError) as conflict:
        await service.review_prompt_version(
            comparison.prompt_version_id, experiment.owner_id, PromptVersionStatus.REJECTED, "changed mind"
        )
    assert conflict.value.status_code == 409
