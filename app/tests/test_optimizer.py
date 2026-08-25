import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from backend.modules.experiments.dispatcher import InlineOptimizationDispatcher
from backend.modules.experiments.optimizer import OptimizationResult
from backend.modules.experiments.prompts import PromptBundle, baseline_prompt
from backend.modules.experiments.repository import InMemoryExperimentRepository
from backend.modules.experiments.schemas import (
    ExperimentRecord,
    ExperimentStatus,
    OptimizationRunRecord,
    ProjectSnapshot,
    TargetReference,
)
from backend.modules.experiments.service import ExperimentService
from backend.modules.projects.schemas import MINIMUM_RUNTIME_PROTOCOL_VERSION


class FakeProjects:
    async def require_owned(self, project_id, owner_id):
        return SimpleNamespace(id=project_id, owner_id=owner_id, object_name="sources/project.zip")


class FakeFunctions:
    async def get(self, project_id, function_id):
        return SimpleNamespace(id=function_id, source=f"def {function_id}(): pass")


class FakeStorage:
    def __init__(self):
        self.objects = {}

    async def write(self, object_name, content, content_type):
        self.objects[object_name] = (content, content_type)


class FakeSamples:
    @staticmethod
    def contains(project_id):
        return project_id == "project-1"


class RecordingOptimizationDispatcher:
    def __init__(self):
        self.run_ids = []

    async def dispatch(self, run_id: str, delay_seconds: int = 0) -> None:
        self.run_ids.append(run_id)


@pytest.mark.asyncio
async def test_uploaded_experiment_accepts_the_current_runtime_protocol():
    repository, storage = InMemoryExperimentRepository(), FakeStorage()
    now = datetime.now(UTC)
    refs = [
        TargetReference(
            project_id="uploaded-project",
            function_id=name,
            project="uploaded-project",
            source_file="pkg/core.py",
            symbol=f"pkg.{name}",
        )
        for name in ("train_fn", "validation_fn", "test_fn")
    ]
    keys = [ref.key for ref in refs]
    experiment = ExperimentRecord(
        id="uploaded-experiment",
        owner_id="owner-1",
        project_id="uploaded-project",
        project_ids=["uploaded-project"],
        project_snapshots=[
            ProjectSnapshot(
                project_id="uploaded-project",
                name="Uploaded project",
                source_directory="pkg",
                test_directory="tests",
                runner_project="uploaded-project",
                archive_object="sources/project.zip",
                runtime_bundle_object="runtime/current.tar.gz",
                runtime_protocol_version=MINIMUM_RUNTIME_PROTOCOL_VERSION,
            )
        ],
        targets=refs,
        name="Uploaded GEPA search",
        target_function_ids=keys,
        dataset_splits={"train": [keys[0]], "validation": [keys[1]], "test": [keys[2]]},
        optimization_eligible=True,
        baseline_prompt=baseline_prompt().as_candidate(),
        status=ExperimentStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )
    await repository.create(experiment)
    service = ExperimentService(repository, FakeProjects(), FakeFunctions(), storage)
    dispatcher = RecordingOptimizationDispatcher()
    service.set_optimization_dispatcher(dispatcher)

    run = await service.request_optimization(experiment.id, experiment.owner_id, full_access=True)

    assert run.status == ExperimentStatus.OPTIMIZATION_QUEUED
    assert dispatcher.run_ids == [run.id]


@pytest.mark.asyncio
async def test_failed_optimization_can_be_retried_with_a_new_run():
    repository, storage = InMemoryExperimentRepository(), FakeStorage()
    now = datetime.now(UTC)
    refs = [
        TargetReference(
            project_id="project-1",
            function_id=name,
            project="project",
            source_file="src/pkg.py",
            symbol=f"pkg.{name}",
        )
        for name in ("train_fn", "validation_fn", "test_fn")
    ]
    keys = [ref.key for ref in refs]
    old_run = OptimizationRunRecord(
        id="failed-run",
        experiment_id="retry-experiment",
        status=ExperimentStatus.FAILED,
        parent_prompt_digest="parent",
        error_message="old image rejected missing_coverage",
        created_at=now,
        finished_at=now,
    )
    experiment = ExperimentRecord(
        id="retry-experiment",
        owner_id="owner-1",
        project_id="project-1",
        project_ids=["project-1"],
        targets=refs,
        name="Retry GEPA search",
        target_function_ids=keys,
        dataset_splits={"train": [keys[0]], "validation": [keys[1]], "test": [keys[2]]},
        optimization_eligible=True,
        baseline_prompt=baseline_prompt().as_candidate(),
        status=ExperimentStatus.FAILED,
        optimization_run_id=old_run.id,
        created_at=now,
        updated_at=now,
    )
    await repository.create(experiment)
    await repository.create_optimization_run(old_run)
    service = ExperimentService(repository, FakeProjects(), FakeFunctions(), storage)
    dispatcher = RecordingOptimizationDispatcher()
    service.set_optimization_dispatcher(dispatcher)

    retried = await service.request_optimization(experiment.id, experiment.owner_id, full_access=True)

    assert retried.id != old_run.id
    assert retried.status == ExperimentStatus.OPTIMIZATION_QUEUED
    assert dispatcher.run_ids == [retried.id]
    stored = await repository.get(experiment.id)
    assert stored.optimization_run_id == retried.id
    assert stored.status == ExperimentStatus.OPTIMIZATION_QUEUED


@pytest.mark.asyncio
async def test_optimization_passes_locked_multi_project_snapshot_to_cloud():
    repository, storage = InMemoryExperimentRepository(), FakeStorage()
    now = datetime.now(UTC)
    preset = baseline_prompt()
    prompt = PromptBundle(initial=preset.initial + "\nCustom seed instruction.", error=preset.error)
    refs = [
        TargetReference(
            project_id="project-1",
            function_id=name,
            project="project",
            source_file="src/pkg.py",
            symbol=f"pkg.{name}",
        )
        for name in ("train_fn", "validation_fn", "test_fn")
    ]
    keys = [ref.key for ref in refs]
    experiment = ExperimentRecord(
        id="experiment-1",
        owner_id="owner-1",
        project_id="project-1",
        project_ids=["project-1"],
        project_snapshots=[
            ProjectSnapshot(
                project_id="project-1",
                name="Project",
                source_directory="src",
                test_directory="tests",
                runner_project="project",
            )
        ],
        targets=refs,
        name="GEPA search",
        target_function_ids=keys,
        dataset_splits={"train": [keys[0]], "validation": [keys[1]], "test": [keys[2]]},
        optimization_eligible=True,
        baseline_prompt=prompt.as_candidate(),
        status=ExperimentStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )
    await repository.create(experiment)

    class FakeCloudOptimizer:
        calls = []

        async def optimize(self, **kwargs):
            self.calls.append(kwargs)
            assert kwargs["vertexai_project"] == "project-7df9f963-9fe0-4b76-b3d"
            assert kwargs["baseline"].digest() == prompt.digest()
            assert [target.id for target in kwargs["train"]] == [keys[0]]
            assert [target.id for target in kwargs["validation"]] == [keys[1]]
            assert [target.id for target in kwargs["holdout"]] == [keys[2]]
            candidate = PromptBundle(initial=prompt.initial + "\nPrefer boundary cases.", error=prompt.error)
            return OptimizationResult(
                candidate,
                0.8,
                0.4,
                2,
                5,
                {
                    "final_validation": {
                        "promoted": True,
                        "absolute_gain": 0.4,
                        "baseline_aggregate_coverage": {"score": 0.4},
                        "optimized_aggregate_coverage": {"score": 0.8},
                        "baseline_results": [
                            {
                                "coverage": {
                                    "gained_branches": [[10, 11], [10, 12]],
                                }
                            }
                        ],
                    }
                },
            )

    cloud = FakeCloudOptimizer()
    service = ExperimentService(
        repository,
        FakeProjects(),
        FakeFunctions(),
        storage,
        cloud_optimizer=cloud,
        samples=FakeSamples(),
        admin_vertexai_project="project-7df9f963-9fe0-4b76-b3d",
    )
    service.set_optimization_dispatcher(InlineOptimizationDispatcher(service.execute_optimization))
    run = await service.request_optimization(experiment.id, experiment.owner_id, full_access=True)

    assert run.status == ExperimentStatus.OPTIMIZATION_SUCCEEDED
    assert run.candidate_validation_score == 0.8
    assert run.final_validation["promoted"] is True
    assert "baseline_results" not in run.final_validation
    gepa_artifact = next(
        content for object_name, (content, _) in storage.objects.items() if object_name.endswith("/gepa_result.json")
    )
    assert json.loads(gepa_artifact)["final_validation"]["baseline_results"][0]["coverage"]["gained_branches"] == [
        [10, 11],
        [10, 12],
    ]
    assert len(cloud.calls) == 1
    stored_experiment = await repository.get(experiment.id)
    assert stored_experiment.baseline_run_id is None
    assert stored_experiment.comparison_run_id is not None
    comparison = await repository.get_comparison_run(stored_experiment.comparison_run_id)
    assert comparison.status == ExperimentStatus.IN_REVIEW
    await service.execute_optimization(run.id)
    assert len(repository.comparison_runs) == 1
    assert len(repository.prompt_versions) == 1
