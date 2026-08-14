import json
import threading
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from backend.modules.experiments.cloud_optimizer import CloudRunJobGepaOptimizer
from backend.modules.experiments.optimizer import OptimizationTarget
from backend.modules.experiments.prompts import baseline_prompt
from backend.modules.experiments.schemas import ExperimentSettings


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
            gepa_seed=19,
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
    assert job_args[job_args.index("--gepa-seed") + 1] == "19"
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
