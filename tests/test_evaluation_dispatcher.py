from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from cloud.evaluation_dispatcher import RemoteEvaluationBackend
from src.optimization.models import ExperimentConfig, SymbolTarget
from src.promptopt_pause import ModelRateLimitPauseError


class _Blob:
    def __init__(self, values: dict[str, bytes], name: str):
        self.values = values
        self.name = name

    def upload_from_string(self, value, content_type=None):
        del content_type
        self.values[self.name] = value.encode() if isinstance(value, str) else bytes(value)

    def download_as_bytes(self):
        return self.values[self.name]

    def exists(self):
        return self.name in self.values

    def delete(self):
        self.values.pop(self.name, None)


class _Bucket:
    def __init__(self, values: dict[str, bytes]):
        self.values = values

    def blob(self, name: str):
        return _Blob(self.values, name)


class _Storage:
    def __init__(self):
        self.values: dict[str, bytes] = {}

    def bucket(self, name: str):
        assert name == "bucket"
        return _Bucket(self.values)


class _Response:
    status_code = 200
    text = ""

    @staticmethod
    def json():
        return {}


class _Session:
    def __init__(self, storage: _Storage):
        self.storage = storage
        self.urls: list[str] = []
        self.pause_next = False

    def post(self, url: str, *, json: dict, timeout: int):
        assert timeout == 30
        self.urls.append(url)
        args = json["overrides"]["containerOverrides"][0]["args"]
        request_object = args[args.index("--request-object") + 1]
        result_object = args[args.index("--result-object") + 1]
        request = __import__("json").loads(self.storage.values[request_object])
        response = {
            "schema_version": 1,
            "request_id": request["request_id"],
        }
        if self.pause_next:
            self.pause_next = False
            response.update(status="paused", error="provider quota")
        elif request["operation"] == "optimizer_test":
            response.update(
                status="succeeded",
                optimizer_test={
                    "experiment_id": request["experiment_id"],
                    "pytest_passed": True,
                    "score": 0.5,
                },
            )
        elif request["operation"] == "final_generation":
            artifact = b"immutable-final-suite"
            self.storage.values[request["artifact_object"]] = artifact
            response.update(
                status="succeeded",
                final_generation={
                    "schema_version": 2,
                    "status": "completed",
                    "metrics": {"target_count": len(request["targets"])},
                },
                artifact_object=request["artifact_object"],
                artifact_sha256=hashlib.sha256(artifact).hexdigest(),
            )
        elif request["operation"] == "final_replay":
            response.update(
                status="succeeded",
                final_replay={
                    "schema_version": 1,
                    "status": "passed",
                    "pytest_exit_code": 0,
                    "artifact_sha256": request["suite_artifact_sha256"],
                    "test_file_count": 1,
                },
            )
        else:
            targets = request["targets"]
            response.update(
                status="succeeded",
                record={
                    "run_id": f"worker-{request['project']}",
                    "split": request["split"],
                    "targets": targets,
                    "command": ["worker"],
                    "started_at": "2026-01-01T00:00:00Z",
                    "finished_at": "2026-01-01T00:00:01Z",
                    "exit_code": 0,
                    "elapsed_seconds": 1,
                    "results": [
                        {
                            "target": target,
                            "score": {"score": 0.5, "valid": True},
                            "feedback": f"worker {request['project']}",
                            "attempt_traces": [],
                        }
                        for target in targets
                    ],
                },
            )
        self.storage.values[result_object] = __import__("json").dumps(response).encode()
        return _Response()


def _backend(tmp_path: Path):
    storage = _Storage()
    session = _Session(storage)
    config = ExperimentConfig(
        project_root=tmp_path,
        package_dir=tmp_path,
        tests_dir=tmp_path,
        artifacts_dir=tmp_path / "artifacts",
        coverup_model="model",
        max_concurrency=4,
    )
    backend = RemoteEvaluationBackend(
        bucket="bucket",
        artifact_prefix="runs/one",
        manifest={
            "schema_version": 2,
            "projects": [
                {
                    "kind": "uploaded",
                    "project": "uploaded",
                    "python_version": "3.13",
                    "runtime_digest": "digest-uploaded",
                    "runtime_image": "image@sha256:one",
                    "runtime_worker_job": "projects/p/locations/r/jobs/eval-uploaded-digest",
                    "source_archive_sha256": "a" * 64,
                    "runtime_bundle_sha256": "b" * 64,
                    "archive_object": "uploaded.zip",
                    "runtime_bundle_object": "runtime.tar.gz",
                },
                {
                    "kind": "sample",
                    "project": "isort",
                    "sample_slug": "isort",
                    "runtime_digest": "sample:isort",
                },
            ],
        },
        jobs={
            "3.13": "projects/p/locations/r/jobs/eval-py313",
            "sample": "projects/p/locations/r/jobs/eval-sample",
        },
        config=config,
        storage_client=storage,
        authorized_session=session,
        sleep=lambda _: None,
    )
    return backend, storage, session


def test_remote_backend_dispatches_each_project_and_preserves_target_order(tmp_path):
    backend, _, session = _backend(tmp_path)
    prompt = tmp_path / "prompt.json"
    prompt.write_text("{}", encoding="utf-8")
    targets = [
        SymbolTarget("uploaded", "pkg/a.py", "a", "validation"),
        SymbolTarget("isort", "isort/core.py", "process", "validation"),
        SymbolTarget("uploaded", "pkg/b.py", "b", "validation"),
    ]

    record = backend.evaluate_batch(
        targets,
        prompt,
        candidate_id="candidate",
        split="validation",
        workspace_kind="candidate",
    )

    assert [item.target for item in record.results] == targets
    assert {item.feedback for item in record.results} == {"worker uploaded", "worker isort"}
    assert any(url.endswith("/eval-uploaded-digest:run") for url in session.urls)
    assert not any(url.endswith("/eval-py313:run") for url in session.urls)
    assert any(url.endswith("/eval-sample:run") for url in session.urls)


def test_remote_backend_forwards_remote_pause_to_coordinator_signal(tmp_path, monkeypatch):
    backend, _, session = _backend(tmp_path)
    prompt = tmp_path / "prompt.json"
    prompt.write_text("{}", encoding="utf-8")
    target = SymbolTarget("uploaded", "pkg/a.py", "a", "train")
    session.pause_next = True
    pause_file = tmp_path / "pause_signal.json"
    monkeypatch.setenv("PROMPTOPT_PAUSE_FILE", str(pause_file))

    with pytest.raises(ModelRateLimitPauseError, match="provider quota"):
        backend.evaluate_batch(
            [target],
            prompt,
            candidate_id="candidate",
            split="train",
            workspace_kind="candidate",
        )

    payload = __import__("json").loads(pause_file.read_text(encoding="utf-8"))
    assert payload["status_code"] == 429
    assert payload["model"] == "model"
    assert "provider quota" in payload["message"]


def test_remote_backend_retries_same_durable_request_after_pause(tmp_path, monkeypatch):
    backend, _, session = _backend(tmp_path)
    prompt = tmp_path / "prompt.json"
    prompt.write_text("{}", encoding="utf-8")
    target = SymbolTarget("uploaded", "pkg/a.py", "a", "train")
    session.pause_next = True
    monkeypatch.delenv("PROMPTOPT_PAUSE_FILE", raising=False)

    with pytest.raises(ModelRateLimitPauseError, match="provider quota"):
        backend.evaluate_batch(
            [target],
            prompt,
            candidate_id="candidate",
            split="train",
            workspace_kind="candidate",
        )

    record = backend.evaluate_batch(
        [target],
        prompt,
        candidate_id="candidate",
        split="train",
        workspace_kind="candidate",
    )
    assert record.results[0].score["score"] == 0.5
    assert len(session.urls) == 2


def test_remote_backend_dispatches_optimizer_diagnostic_to_target_runtime(tmp_path):
    backend, _, session = _backend(tmp_path)
    result = backend.evaluate_optimizer_test(
        SymbolTarget("uploaded", "pkg/a.py", "a", "train"),
        "def test_a():\n    assert True\n",
        experiment_id="diagnostic-1",
    )
    assert result == {"experiment_id": "diagnostic-1", "pytest_passed": True, "score": 0.5}
    assert session.urls[-1].endswith("/eval-uploaded-digest:run")


def test_remote_backend_does_not_reuse_result_after_execution_config_changes(tmp_path):
    backend, storage, session = _backend(tmp_path)
    prompt = tmp_path / "prompt.json"
    prompt.write_text("{}", encoding="utf-8")
    target = SymbolTarget("uploaded", "pkg/a.py", "a", "train")

    backend.evaluate_batch(
        [target],
        prompt,
        candidate_id="candidate",
        split="train",
        workspace_kind="candidate",
    )
    first_requests = sorted(name for name in storage.values if name.endswith("/request.json"))
    backend.config.max_attempts += 1
    backend.evaluate_batch(
        [target],
        prompt,
        candidate_id="candidate",
        split="train",
        workspace_kind="candidate",
    )
    second_requests = sorted(name for name in storage.values if name.endswith("/request.json"))

    assert len(session.urls) == 2
    assert len(first_requests) == 1
    assert len(second_requests) == 2
    assert first_requests[0] in second_requests


def test_remote_backend_routes_final_generation_to_project_worker(tmp_path):
    backend, _, session = _backend(tmp_path)
    prompt = tmp_path / "prompt.json"
    prompt.write_text('{"initial":"a","error":"b"}', encoding="utf-8")
    targets = [SymbolTarget("uploaded", "pkg/a.py", "a", "final")]

    output = backend.generate_final_project("uploaded", targets, prompt, seed=17)

    assert output["result"]["metrics"]["target_count"] == 1
    assert output["artifact_object"].endswith(".zip")
    assert output["replay"]["status"] == "passed"
    assert output["replay"]["pytest_exit_code"] == 0
    assert len(session.urls) == 2
    assert session.urls[-1].endswith("/eval-uploaded-digest:run")
