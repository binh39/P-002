import io
import zipfile
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from src.modules.experiments.dispatcher import InlineOptimizationDispatcher
from src.modules.experiments.optimizer import OptimizationResult
from src.modules.experiments.prompts import PromptBundle, baseline_prompt
from src.modules.experiments.repository import InMemoryExperimentRepository
from src.modules.experiments.schemas import (
    BaselineRunRecord,
    ExperimentRecord,
    ExperimentStatus,
    ProjectSnapshot,
    TargetReference,
)
from src.modules.experiments.service import ExperimentService


class FakeProjects:
    async def require_owned(self, project_id, owner_id):
        return SimpleNamespace(id=project_id, owner_id=owner_id, object_name="sources/project.zip")


class FakeFunctions:
    async def get(self, project_id, function_id):
        return SimpleNamespace(id=function_id, source=f"def {function_id}(): pass")


class FakeStorage:
    def __init__(self):
        self.objects = {}

    async def read(self, object_name):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("src/pkg.py", "def train_fn(): pass\n")
            archive.writestr("tests/test_pkg.py", "")
        return buffer.getvalue()

    async def write(self, object_name, content, content_type):
        self.objects[object_name] = (content, content_type)


@pytest.mark.asyncio
async def test_optimization_passes_locked_multi_project_snapshot_to_cloud():
    repository, storage = InMemoryExperimentRepository(), FakeStorage()
    now, prompt = datetime.now(UTC), baseline_prompt()
    refs = [TargetReference(
        project_id="project-1", function_id=name, project="project",
        source_file="src/pkg.py", symbol=f"pkg.{name}",
    ) for name in ("train_fn", "validation_fn", "test_fn")]
    keys = [ref.key for ref in refs]
    experiment = ExperimentRecord(
        id="experiment-1", owner_id="owner-1", project_id="project-1", project_ids=["project-1"],
        project_snapshots=[ProjectSnapshot(
            project_id="project-1", name="Project", source_directory="src",
            test_directory="tests", runner_project="project",
        )],
        targets=refs, name="GEPA search", target_function_ids=keys,
        dataset_splits={"train": [keys[0]], "validation": [keys[1]], "test": [keys[2]]},
        optimization_eligible=True, status=ExperimentStatus.BASELINE_SUCCEEDED,
        baseline_run_id="baseline-1", created_at=now, updated_at=now,
    )
    await repository.create(experiment)
    await repository.create_run(BaselineRunRecord(
        id="baseline-1", experiment_id=experiment.id, status=ExperimentStatus.BASELINE_SUCCEEDED,
        target_count=3, coverage_score=0.4, prompt_digest=prompt.digest(), created_at=now, finished_at=now,
    ))

    class FakeCloudOptimizer:
        calls = []

        async def optimize(self, **kwargs):
            self.calls.append(kwargs)
            assert [target.id for target in kwargs["train"]] == [keys[0]]
            assert [target.id for target in kwargs["validation"]] == [keys[1]]
            assert [target.id for target in kwargs["holdout"]] == [keys[2]]
            candidate = PromptBundle(initial=prompt.initial + "\nPrefer boundary cases.", error=prompt.error)
            return OptimizationResult(candidate, 0.8, 0.4, 2, 5, {
                "final_validation": {"promoted": True, "absolute_gain": 0.4}
            })

    cloud = FakeCloudOptimizer()
    service = ExperimentService(
        repository, FakeProjects(), FakeFunctions(), storage, cloud_optimizer=cloud,
    )
    service.set_optimization_dispatcher(InlineOptimizationDispatcher(service.execute_optimization))
    run = await service.request_optimization(experiment.id, experiment.owner_id)

    assert run.status == ExperimentStatus.OPTIMIZATION_SUCCEEDED
    assert run.candidate_validation_score == 0.8
    assert run.final_validation["promoted"] is True
    assert len(cloud.calls) == 1
