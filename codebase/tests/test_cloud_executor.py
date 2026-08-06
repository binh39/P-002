import json

import pytest

from src.modules.experiments.cloud_executor import CloudRunJobCoverUpExecutor
from src.modules.experiments.prompts import baseline_prompt


class FakeStorage:
    def __init__(self):
        self.objects = {}

    async def write(self, object_name, content, content_type):
        self.objects[object_name] = (content, content_type)

    async def read(self, object_name):
        return self.objects[object_name][0]


class FakeOperation:
    def __init__(self):
        self.timeout = None

    async def result(self, timeout):
        self.timeout = timeout


class FakeJobsClient:
    def __init__(self, storage):
        self.storage = storage
        self.request = None
        self.operation = FakeOperation()

    async def run_job(self, request):
        self.request = request
        environment = request["overrides"]["container_overrides"][0]["env"]
        prefix = next(item["value"] for item in environment if item["name"] == "PROMPTOPT_JOB_PREFIX")
        result = {
            "status": "succeeded",
            "coverage_score": 0.75,
            "statement_coverage": 0.8,
            "branch_coverage": 0.7,
            "target_metrics": {"pkg.fn": {"valid": True, "score": 0.75}},
            "artifacts": ["coverage_after.json"],
        }
        self.storage.objects[f"{prefix}/result.json"] = (json.dumps(result).encode(), "application/json")
        self.storage.objects[f"{prefix}/artifacts/coverage_after.json"] = (b"{}", "application/json")
        return self.operation


class FailedOperation:
    async def result(self, timeout):
        del timeout
        raise RuntimeError("execution task failed")


class FailedJobsClient(FakeJobsClient):
    async def run_job(self, request):
        self.request = request
        environment = request["overrides"]["container_overrides"][0]["env"]
        prefix = next(item["value"] for item in environment if item["name"] == "PROMPTOPT_JOB_PREFIX")
        result = {"status": "failed", "error": "Generated tests failed coverage validation"}
        self.storage.objects[f"{prefix}/result.json"] = (json.dumps(result).encode(), "application/json")
        return FailedOperation()


@pytest.mark.asyncio
async def test_cloud_run_job_executor_uses_gcs_manifest_and_environment_references_only():
    storage = FakeStorage()
    client = FakeJobsClient(storage)
    executor = CloudRunJobCoverUpExecutor(
        client=client,
        storage=storage,
        bucket="private-bucket",
        job_name="projects/project/locations/region/jobs/runner",
        timeout_seconds=900,
    )

    result = await executor.execute(b"source archive", "src", ["pkg.fn"], baseline_prompt())

    assert result.coverage_score == 0.75
    assert result.artifacts == {"coverage_after.json": b"{}"}
    assert client.request["name"].endswith("/jobs/runner")
    overrides = client.request["overrides"]
    assert overrides["task_count"] == 1
    assert overrides["timeout"] == "900s"
    environment = overrides["container_overrides"][0]["env"]
    assert {item["name"] for item in environment} == {"PROMPTOPT_JOB_BUCKET", "PROMPTOPT_JOB_PREFIX"}
    prefix = next(item["value"] for item in environment if item["name"] == "PROMPTOPT_JOB_PREFIX")
    spec = json.loads(storage.objects[f"{prefix}/spec.json"][0])
    assert spec["symbols"] == ["pkg.fn"]
    assert "source archive" not in json.dumps(client.request)
    assert "initial" not in json.dumps(client.request)
    assert client.operation.timeout == 960


@pytest.mark.asyncio
async def test_cloud_run_job_executor_surfaces_failed_result_manifest():
    storage = FakeStorage()
    executor = CloudRunJobCoverUpExecutor(
        client=FailedJobsClient(storage),
        storage=storage,
        bucket="private-bucket",
        job_name="projects/project/locations/region/jobs/runner",
        timeout_seconds=900,
    )

    with pytest.raises(RuntimeError, match="Generated tests failed coverage validation"):
        await executor.execute(b"source archive", "src", ["pkg.fn"], baseline_prompt())
