import json
import threading
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from backend.modules.experiments.cloud_optimizer import CloudRunJobGepaOptimizer, OptimizationPausedError
from backend.modules.experiments.optimizer import OptimizationTarget
from backend.modules.experiments.prompts import baseline_prompt
from backend.modules.experiments.schemas import ExperimentSettings, ProjectSnapshot


class FakeStorage:
    def __init__(self):
        self.objects = {}

    async def write(self, object_name, content, content_type):
        self.objects[object_name] = (content, content_type)

    async def read(self, object_name):
        return self.objects[object_name][0]


class FakeOperation:
    def result(self, timeout):
        pytest.fail("the API worker must not wait for a 24-hour Cloud Run Job")


class FakeJobsClient:
    def __init__(self, storage):
        self.storage = storage
        self.request = None
        self.thread_id = None

    def run_job(self, request):
        self.request = request
        self.thread_id = threading.get_ident()
        args = request["overrides"]["container_overrides"][0]["args"]
        prefix = args[args.index("--artifacts-name") + 1]
        prompt = baseline_prompt()
        candidate = {"initial": prompt.initial + "\nPrefer explicit boundary assertions.", "error": prompt.error}
        payloads = {
            "job_result.json": {"status": "succeeded", "missing_artifacts": []},
            "optimized_program.json": {
                "best_index": 1,
                "best_candidate": candidate,
                "validation_scores": [0.2, 0.7],
                "total_metric_calls": 12,
                "candidates": [prompt.as_candidate(), candidate],
            },
            "final_validation.json": {"promoted": True, "absolute_gain": 0.5},
            "prompts/gepa_proposed.json": candidate,
        }
        for name, payload in payloads.items():
            self.storage.objects[f"{prefix}/{name}"] = (json.dumps(payload).encode(), "application/json")
        return FakeOperation()


class FakeLoggingClient:
    def __init__(self, execution_id):
        self.execution_id = execution_id
        self.filters = []

    def list_entries(self, *, filter_, order_by, page_size):
        self.filters.append(filter_)
        if len(self.filters) == 1:
            return iter(
                [
                    SimpleNamespace(
                        labels={"run.googleapis.com/execution_name": "promptopt-gepa-runner-ab123"},
                        payload=f"==> Upload target: gs://bucket/runner-jobs/gepa/{self.execution_id}/artifacts/",
                        timestamp=datetime(2026, 8, 10, tzinfo=UTC),
                    )
                ]
            )
        return iter(
            [
                SimpleNamespace(
                    labels={"run.googleapis.com/execution_name": "promptopt-gepa-runner-ab123"},
                    payload="Iteration 0: Base program full valset score: 0.25 over 2 / 2 examples",
                    timestamp=datetime(2026, 8, 10, tzinfo=UTC),
                )
            ]
        )


class FakeExecutionsClient:
    def __init__(self):
        self.request = None

    def cancel_execution(self, *, request):
        self.request = request
        return SimpleNamespace()


@pytest.mark.asyncio
async def test_cloud_gepa_optimizer_uses_isolated_web_prefix_and_maps_result():
    event_loop_thread = threading.get_ident()
    storage = FakeStorage()
    client = FakeJobsClient(storage)
    optimizer = CloudRunJobGepaOptimizer(
        client=client,
        storage=storage,
        bucket="private-source-bucket",
        job_name="projects/project/locations/region/jobs/promptopt-gepa-runner",
        timeout_seconds=86400,
    )
    targets = {
        split: [
            OptimizationTarget(
                id=f"{split}-1",
                symbol=f"pkg.{split}",
                split=split,
                source_file="pkg/module.py",
                project="isort",
            )
        ]
        for split in ("train", "validation", "test")
    }

    result = await optimizer.optimize(
        baseline=baseline_prompt(),
        train=targets["train"],
        validation=targets["validation"],
        holdout=targets["test"],
        settings=ExperimentSettings(
            coverup_model="vertex_ai/gemini-3.5-flash-lite",
            optimize_model="vertex_ai/gemini-3.1-pro-preview",
            max_metric_calls=30,
            reflection_minibatch_size=3,
        ),
    )

    request_text = json.dumps(client.request)
    assert "prompt_optimization_v3" not in request_text
    assert "runner-jobs/gepa/" in request_text
    assert client.request["name"].endswith("/promptopt-gepa-runner")
    assert client.request["overrides"]["timeout"] == "86400s"
    job_args = client.request["overrides"]["container_overrides"][0]["args"]
    assert job_args[job_args.index("--metric-calls") + 1] == "30"
    assert job_args[job_args.index("--repeat-tests") + 1] == "5"
    assert job_args[job_args.index("--evaluation-replicates") + 1] == "1"
    assert job_args[job_args.index("--reflection-minibatch-size") + 1] == "3"
    environment = {item["name"]: item["value"] for item in client.request["overrides"]["container_overrides"][0]["env"]}
    assert environment == {
        "COVERUP_MODEL": "vertex_ai/gemini-3.5-flash-lite",
        "OPTIMIZE_MODEL": "vertex_ai/gemini-3.1-pro-preview",
    }
    assert client.thread_id != event_loop_thread
    assert result.score == 0.7
    assert result.baseline_score == 0.2
    assert result.candidate_count == 2
    assert result.metric_calls == 12
    dataset_object = next(name for name in storage.objects if name.endswith("inputs/dataset.jsonl"))
    rows = [json.loads(line) for line in storage.objects[dataset_object][0].decode().splitlines()]
    assert {row["split"] for row in rows} == {"train", "validation", "test"}
    assert not any(name.endswith("source.zip") for name in storage.objects)
    assert not any(name.endswith("project-layouts.json") for name in storage.objects)

    await optimizer.start(
        baseline=baseline_prompt(),
        train=targets["train"],
        validation=targets["validation"],
        holdout=targets["test"],
        settings=ExperimentSettings(),
        vertexai_project="project-7df9f963-9fe0-4b76-b3d",
    )
    admin_environment = {
        item["name"]: item["value"] for item in client.request["overrides"]["container_overrides"][0]["env"]
    }
    assert admin_environment["VERTEXAI_PROJECT"] == "project-7df9f963-9fe0-4b76-b3d"


def test_experiment_settings_restrict_reflection_minibatch_size():
    assert ExperimentSettings(reflection_minibatch_size=1).reflection_minibatch_size == 1
    assert ExperimentSettings().reflection_minibatch_size == 5
    with pytest.raises(ValueError, match="less than or equal to 5"):
        ExperimentSettings(reflection_minibatch_size=6)


@pytest.mark.asyncio
async def test_cloud_gepa_optimizer_copies_uploaded_project_into_job_prefix():
    storage = FakeStorage()
    storage.objects["users/u/uploads/source.zip"] = (b"zip-content", "application/zip")
    storage.objects["runner-jobs/runtime/ready/runtime.tar.gz"] = (
        b"runtime-content",
        "application/gzip",
    )
    client = FakeJobsClient(storage)
    optimizer = CloudRunJobGepaOptimizer(
        client=client,
        storage=storage,
        bucket="private-source-bucket",
        job_name="projects/project/locations/region/jobs/promptopt-gepa-runner",
        timeout_seconds=86400,
    )
    target = OptimizationTarget(
        id="target-1",
        symbol="add",
        split="train",
        source_file="module.py",
        project="uploaded",
    )
    snapshot = ProjectSnapshot(
        project_id="project-1",
        name="Uploaded",
        source_directory="pkg",
        test_directory="tests",
        runner_project="uploaded",
        archive_object="users/u/uploads/source.zip",
        runtime_artifact_prefix="runner-jobs/runtime/ready",
        runtime_environment_id="environment-1",
        runtime_bundle_object="runner-jobs/runtime/ready/runtime.tar.gz",
        runtime_digest="runtime-digest",
        runtime_image="promptopt-runtime-py312@sha256:image",
        runtime_worker_job="projects/project/locations/region/jobs/eval-project",
        source_archive_sha256="a" * 64,
        runtime_bundle_sha256="b" * 64,
        python_version="3.12",
    )

    await optimizer.start(
        baseline=baseline_prompt(),
        train=[target],
        validation=[
            OptimizationTarget(
                id="target-2",
                symbol="add",
                split="validation",
                source_file="module.py",
                project="uploaded",
            )
        ],
        holdout=None,
        settings=ExperimentSettings(),
        projects=[snapshot],
    )

    args = client.request["overrides"]["container_overrides"][0]["args"]
    manifest_name = args[args.index("--project-manifest-object") + 1]
    manifest = json.loads(storage.objects[manifest_name][0])
    copied_name = manifest["projects"][0]["archive_object"]
    assert copied_name.startswith("runner-jobs/gepa/")
    assert storage.objects[copied_name][0] == b"zip-content"
    assert manifest["schema_version"] == 3
    assert manifest["projects"][0]["runtime_digest"] == "runtime-digest"
    assert manifest["projects"][0]["source_archive_sha256"] == "a" * 64
    assert manifest["projects"][0]["runtime_bundle_sha256"] == "b" * 64
    copied_bundle = manifest["projects"][0]["runtime_bundle_object"]
    assert copied_bundle.startswith("runner-jobs/gepa/")
    assert storage.objects[copied_bundle][0] == b"runtime-content"


@pytest.mark.asyncio
async def test_cloud_gepa_optimizer_gives_sample_project_the_same_worker_contract():
    storage = FakeStorage()
    client = FakeJobsClient(storage)
    optimizer = CloudRunJobGepaOptimizer(
        client=client,
        storage=storage,
        bucket="private-source-bucket",
        job_name="projects/project/locations/region/jobs/promptopt-gepa-runner",
        timeout_seconds=86400,
    )
    snapshot = ProjectSnapshot(
        project_id="sample:isort",
        name="isort",
        commit="sample-commit",
        source_directory="isort",
        test_directory="tests",
        runner_project="isort",
        python_version="3.12",
    )
    train = OptimizationTarget(
        id="train",
        symbol="process",
        split="train",
        source_file="isort/core.py",
        project="isort",
    )
    validation = OptimizationTarget(
        id="validation",
        symbol="process",
        split="validation",
        source_file="isort/core.py",
        project="isort",
    )

    await optimizer.start(
        baseline=baseline_prompt(),
        train=[train],
        validation=[validation],
        holdout=None,
        settings=ExperimentSettings(),
        projects=[snapshot],
    )

    args = client.request["overrides"]["container_overrides"][0]["args"]
    manifest_name = args[args.index("--project-manifest-object") + 1]
    project = json.loads(storage.objects[manifest_name][0])["projects"][0]
    assert project == {
        "kind": "sample",
        "project": "isort",
        "sample_slug": "isort",
        "runtime_digest": "sample:isort:sample-commit",
        "runtime_image": "bundled-gepa-image",
        "execution_mode": "generic_worker_bundle",
        "python_version": "3.12",
        "source_directory": "isort",
        "test_directory": "tests",
    }


@pytest.mark.asyncio
async def test_cloud_gepa_optimizer_surfaces_the_worker_root_cause():
    storage = FakeStorage()
    prefix = "runner-jobs/gepa/failed/artifacts"
    storage.objects[f"{prefix}/job_result.json"] = (
        json.dumps(
            {
                "status": "failed",
                "return_code": 1,
                "missing_artifacts": ["optimized_program.json"],
                "error": "RuntimeError: baseline target could not be measured",
            }
        ).encode(),
        "application/json",
    )
    optimizer = CloudRunJobGepaOptimizer(
        client=FakeJobsClient(storage),
        storage=storage,
        bucket="bucket",
        job_name="projects/project/locations/region/jobs/promptopt-gepa-runner",
        timeout_seconds=86400,
    )

    with pytest.raises(RuntimeError, match="baseline target could not be measured"):
        await optimizer.collect(prefix)


@pytest.mark.asyncio
async def test_cloud_gepa_optimizer_surfaces_resumable_pause_and_passes_checkpoint_prefix():
    storage = FakeStorage()
    prefix = "runner-jobs/gepa/paused/artifacts"
    storage.objects[f"{prefix}/job_result.json"] = (
        json.dumps(
            {
                "status": "paused",
                "pause": {"reason": "rate_limited", "message": "Vertex returned HTTP 429"},
            }
        ).encode(),
        "application/json",
    )
    client = FakeJobsClient(storage)
    optimizer = CloudRunJobGepaOptimizer(
        client=client,
        storage=storage,
        bucket="bucket",
        job_name="projects/project/locations/region/jobs/promptopt-gepa-runner",
        timeout_seconds=86400,
    )

    with pytest.raises(OptimizationPausedError, match="HTTP 429") as captured:
        await optimizer.collect(prefix)
    assert captured.value.pause["reason"] == "rate_limited"

    target = OptimizationTarget(
        id="target-1",
        symbol="pkg.fn",
        split="train",
        source_file="pkg.py",
        project="sample",
    )
    validation = OptimizationTarget(
        id="target-2",
        symbol="pkg.other",
        split="validation",
        source_file="pkg.py",
        project="sample",
    )
    await optimizer.start(
        baseline=baseline_prompt(),
        train=[target],
        validation=[validation],
        holdout=None,
        settings=ExperimentSettings(),
        resume_artifacts_prefix=prefix,
    )
    args = client.request["overrides"]["container_overrides"][0]["args"]
    assert args[args.index("--resume-artifacts-name") + 1] == prefix


@pytest.mark.asyncio
async def test_cloud_evolution_resolves_execution_label_and_parses_stdout():
    execution_id = "a1b2c3"
    logging_client = FakeLoggingClient(execution_id)
    optimizer = CloudRunJobGepaOptimizer(
        client=FakeJobsClient(FakeStorage()),
        storage=FakeStorage(),
        bucket="bucket",
        job_name="projects/project/locations/region/jobs/promptopt-gepa-runner",
        timeout_seconds=86400,
        logging_client=logging_client,
    )

    result = await optimizer.evolution(
        f"runner-jobs/gepa/{execution_id}/artifacts",
        started_at=datetime(2026, 8, 10, tzinfo=UTC),
    )

    assert result.available is True
    assert result.iterations[0].best_score == 0.25
    assert 'labels."run.googleapis.com/execution_name"="promptopt-gepa-runner-ab123"' in logging_client.filters[1]


@pytest.mark.asyncio
async def test_cloud_cancel_targets_the_execution_resolved_from_stdout():
    execution_id = "d4e5f6"
    executions = FakeExecutionsClient()
    optimizer = CloudRunJobGepaOptimizer(
        client=FakeJobsClient(FakeStorage()),
        storage=FakeStorage(),
        bucket="bucket",
        job_name="projects/project/locations/region/jobs/promptopt-gepa-runner",
        timeout_seconds=86400,
        logging_client=FakeLoggingClient(execution_id),
        executions_client=executions,
    )

    name = await optimizer.cancel(
        f"runner-jobs/gepa/{execution_id}/artifacts",
        started_at=datetime(2026, 8, 10, tzinfo=UTC),
    )

    assert name == "projects/project/locations/region/jobs/promptopt-gepa-runner/executions/promptopt-gepa-runner-ab123"
    assert executions.request == {"name": name}
