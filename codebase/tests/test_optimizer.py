from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from src.modules.experiments.dispatcher import InlineOptimizationDispatcher
from src.modules.experiments.executor import BaselineExecution
from src.modules.experiments.optimizer import (
    CoverUpGepaAdapter,
    OptimizationResult,
    OptimizationTarget,
)
from src.modules.experiments.prompts import PromptBundle, baseline_prompt
from src.modules.experiments.repository import InMemoryExperimentRepository
from src.modules.experiments.schemas import (
    BaselineRunRecord,
    ExperimentRecord,
    ExperimentStatus,
)
from src.modules.experiments.service import ExperimentService


class FakeExecutor:
    def __init__(self):
        self.calls = 0
        self.image = "fake-runner"
        self.timeout_seconds = 10
        self.memory_mb = 512
        self.cpu = 1
        self.network_mode = "none"

    async def execute(self, archive, source_directory, symbols, prompt):
        del archive, source_directory, prompt
        self.calls += 1
        symbol = symbols[0]
        metric = {
            "valid": True,
            "covered_statements": 3,
            "num_statements": 4,
            "covered_branches": 1,
            "num_branches": 2,
            "score": 0.6,
        }
        return BaselineExecution(
            coverage_score=0.6,
            statement_coverage=0.75,
            branch_coverage=0.5,
            artifacts={"attempt_trace.jsonl": b'{"event":"generated"}\n'},
            target_metrics={symbol: metric},
        )


def test_gepa_adapter_uses_coverage_reward_and_prompt_digest_cache():
    executor = FakeExecutor()
    adapter = CoverUpGepaAdapter(executor, b"archive", "src")
    target = OptimizationTarget(id="fn-1", symbol="pkg.calculate", source="def calculate(): ...", split="train")

    first = adapter.evaluate([target], baseline_prompt().as_candidate(), capture_traces=True)
    second = adapter.evaluate([target], baseline_prompt().as_candidate(), capture_traces=False)

    assert first.scores == [0.6]
    assert first.trajectories[0]["trace"] == [{"event": "generated"}]
    assert second.scores == [0.6]
    assert executor.calls == 1


def test_gepa_adapter_rejects_invalid_candidate_before_execution():
    executor = FakeExecutor()
    adapter = CoverUpGepaAdapter(executor, b"archive", "src")
    target = OptimizationTarget(id="fn-1", symbol="pkg.calculate", source="source", split="train")

    result = adapter.evaluate([target], {"initial": "missing placeholders", "error": "{error}"})

    assert result.scores == [0.0]
    assert executor.calls == 0


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
        return SimpleNamespace(id=function_id, qualified_name=f"pkg.{function_id}", source=f"def {function_id}(): pass")


class FakeStorage:
    def __init__(self):
        self.objects = {}

    async def read(self, object_name):
        assert object_name == "sources/project.zip"
        return b"archive"

    async def write(self, object_name, content, content_type):
        self.objects[object_name] = (content, content_type)


@pytest.mark.asyncio
async def test_optimization_lifecycle_persists_candidate_without_using_test_split(monkeypatch):
    repository = InMemoryExperimentRepository()
    storage = FakeStorage()
    now = datetime.now(UTC)
    prompt = baseline_prompt()
    experiment = ExperimentRecord(
        id="experiment-1",
        owner_id="owner-1",
        project_id="project-1",
        name="GEPA search",
        target_function_ids=["train_fn", "validation_fn", "test_fn"],
        dataset_splits={"train": ["train_fn"], "validation": ["validation_fn"], "test": ["test_fn"]},
        optimization_eligible=True,
        status=ExperimentStatus.BASELINE_SUCCEEDED,
        baseline_run_id="baseline-1",
        created_at=now,
        updated_at=now,
    )
    await repository.create(experiment)
    await repository.create_run(
        BaselineRunRecord(
            id="baseline-1",
            experiment_id=experiment.id,
            status=ExperimentStatus.BASELINE_SUCCEEDED,
            target_count=3,
            coverage_score=0.4,
            prompt_digest=prompt.digest(),
            created_at=now,
            finished_at=now,
        )
    )

    optimization_calls = []

    def fake_optimize(**kwargs):
        optimization_calls.append(kwargs)
        assert [target.id for target in kwargs["train"]] == ["train_fn"]
        assert [target.id for target in kwargs["validation"]] == ["validation_fn"]
        assert "test_fn" not in {target.id for split in (kwargs["train"], kwargs["validation"]) for target in split}
        candidate = PromptBundle(initial=prompt.initial + "\nPrefer boundary cases.", error=prompt.error)
        return OptimizationResult(candidate, 0.8, 0.4, 2, 5, {"best_idx": 1})

    monkeypatch.setattr("src.modules.experiments.service.optimize_prompt", fake_optimize)
    service = ExperimentService(
        repository,
        FakeProjects(),
        FakeFunctions(),
        storage,
        FakeExecutor(),
        "vertex_ai/gemini-test",
        10,
    )
    service.set_optimization_dispatcher(InlineOptimizationDispatcher(service.execute_optimization))

    run = await service.request_optimization(experiment.id, experiment.owner_id)

    assert run.status == ExperimentStatus.OPTIMIZATION_SUCCEEDED
    assert run.candidate_validation_score == 0.8
    assert run.parent_prompt_digest == prompt.digest()
    assert set(run.artifact_objects) == {"candidate_prompt.json", "gepa_result.json"}
    assert (await repository.get(experiment.id)).status == ExperimentStatus.OPTIMIZATION_SUCCEEDED

    await service.execute_optimization(run.id)
    assert len(optimization_calls) == 1
