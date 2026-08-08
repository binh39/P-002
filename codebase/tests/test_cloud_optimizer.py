import json
import threading

import pytest

from src.modules.experiments.cloud_optimizer import CloudRunJobGepaOptimizer
from src.modules.experiments.optimizer import OptimizationTarget
from src.modules.experiments.prompts import baseline_prompt
from src.modules.experiments.schemas import ExperimentSettings


class FakeStorage:
    def __init__(self):
        self.objects = {}

    async def write(self, object_name, content, content_type):
        self.objects[object_name] = (content, content_type)

    async def read(self, object_name):
        return self.objects[object_name][0]


class FakeOperation:
    def result(self, timeout):
        assert timeout == 1740


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
            "prompts/gepa_optimized.json": candidate,
        }
        for name, payload in payloads.items():
            self.storage.objects[f"{prefix}/{name}"] = (json.dumps(payload).encode(), "application/json")
        return FakeOperation()


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
        timeout_seconds=1680,
    )
    targets = {
        split: [
            OptimizationTarget(
                id=f"{split}-1",
                symbol=f"pkg.{split}",
                source=f"def {split}(): pass",
                split=split,
                source_file="pkg/module.py",
            )
        ]
        for split in ("train", "validation", "test")
    }

    result = await optimizer.optimize(
        archive=b"zip",
        project_layouts={"uploaded": {"package_dir": "pkg", "tests_dir": "tests"}},
        baseline=baseline_prompt(),
        train=targets["train"],
        validation=targets["validation"],
        holdout=targets["test"],
        settings=ExperimentSettings(
            coverup_model="vertex_ai/gemini-2.5-flash-lite",
            optimize_model="vertex_ai/gemini-3.5-flash",
            max_metric_calls=30,
        ),
    )

    request_text = json.dumps(client.request)
    assert "prompt_optimization_v3" not in request_text
    assert "runner-jobs/gepa/" in request_text
    assert client.request["name"].endswith("/promptopt-gepa-runner")
    assert client.thread_id != event_loop_thread
    environment = client.request["overrides"]["container_overrides"][0]["env"]
    assert environment == [
        {"name": "COVERUP_MODEL", "value": "vertex_ai/gemini-2.5-flash-lite"},
        {"name": "OPTIMIZE_MODEL", "value": "vertex_ai/gemini-3.5-flash"},
    ]
    assert result.score == 0.7
    assert result.baseline_score == 0.2
    assert result.candidate_count == 2
    assert result.metric_calls == 12
    dataset_object = next(name for name in storage.objects if name.endswith("inputs/dataset.jsonl"))
    rows = [json.loads(line) for line in storage.objects[dataset_object][0].decode().splitlines()]
    assert {row["split"] for row in rows} == {"train", "validation", "test"}
