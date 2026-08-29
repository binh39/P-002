from __future__ import annotations

import hashlib
import json
import tarfile
from pathlib import Path

import pytest

from cloud.runtime_image_factory import _build_context, _build_image, _ensure_worker_job, materialize_runtime


class _Response:
    def __init__(self, status_code: int, payload: dict, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self) -> dict:
        return self._payload


class _Session:
    def __init__(self, posts: list[_Response], gets: list[_Response]):
        self.posts = list(posts)
        self.gets = list(gets)
        self.post_calls: list[tuple[str, dict]] = []
        self.get_calls: list[str] = []

    def post(self, url: str, **kwargs):
        self.post_calls.append((url, kwargs))
        return self.posts.pop(0)

    def get(self, url: str, **kwargs):
        del kwargs
        self.get_calls.append(url)
        return self.gets.pop(0)


class _Blob:
    def __init__(self, values: dict[str, bytes], name: str):
        self.values = values
        self.name = name

    def download_to_filename(self, destination: str) -> None:
        Path(destination).write_bytes(self.values[self.name])

    def upload_from_filename(self, source: str, content_type: str | None = None) -> None:
        del content_type
        self.values[self.name] = Path(source).read_bytes()


class _Bucket:
    def __init__(self, values: dict[str, bytes]):
        self.values = values

    def blob(self, name: str) -> _Blob:
        return _Blob(self.values, name)


def test_build_context_requires_a_digest_pinned_base_and_bakes_both_inputs(tmp_path):
    source = tmp_path / "project.zip"
    bundle = tmp_path / "runtime.tar.gz"
    source.write_bytes(b"source")
    bundle.write_bytes(b"runtime")
    context = tmp_path / "context.tar.gz"

    with pytest.raises(RuntimeError, match="pinned by sha256"):
        _build_context("registry/base:latest", source, bundle, context)

    _build_context(f"registry/base@sha256:{'a' * 64}", source, bundle, context)
    with tarfile.open(context, "r:gz") as archive:
        assert set(archive.getnames()) == {"Dockerfile", "project.zip", "runtime.tar.gz"}
        dockerfile = archive.extractfile("Dockerfile").read().decode()
    assert "PROMPTOPT_BAKED_SOURCE_ARCHIVE" in dockerfile
    assert "PROMPTOPT_BAKED_RUNTIME_BUNDLE" in dockerfile


def test_cloud_build_uses_dedicated_builder_and_returns_immutable_digest():
    digest = f"sha256:{'b' * 64}"
    session = _Session(
        [_Response(200, {"name": "projects/p/locations/r/operations/build-one"})],
        [
            _Response(
                200,
                {
                    "done": True,
                    "response": {
                        "status": "SUCCESS",
                        "results": {"images": [{"name": "repo/image:tag", "digest": digest}]},
                    },
                },
            )
        ],
    )

    image = _build_image(
        session,
        project_id="p",
        region="r",
        bucket_name="bucket",
        context_object="runner-jobs/context.tar.gz",
        image_tag="repo/image:tag",
        timeout_seconds=60,
        build_service_account="builder@p.iam.gserviceaccount.com",
        sleep=lambda _seconds: None,
    )

    assert image == f"repo/image@{digest}"
    _, call = session.post_calls[0]
    assert call["json"]["source"]["storageSource"] == {
        "bucket": "bucket",
        "object": "runner-jobs/context.tar.gz",
    }
    assert call["json"]["serviceAccount"] == "projects/p/serviceAccounts/builder@p.iam.gserviceaccount.com"
    assert session.get_calls == ["https://cloudbuild.googleapis.com/v1/projects/p/locations/r/operations/build-one"]


def test_worker_job_is_unique_and_bound_to_exact_image_and_runner():
    image = f"repo/project@sha256:{'c' * 64}"
    session = _Session(
        [_Response(200, {"name": "projects/p/locations/r/operations/job-one"})],
        [_Response(200, {"done": True, "response": {}})],
    )

    job = _ensure_worker_job(
        session,
        project_id="p",
        region="r",
        job_id="promptopt-eval-project-digest",
        image=image,
        runner_service_account="runner@p.iam.gserviceaccount.com",
        model_project_id="models",
        coverup_model="vertex_ai/model",
        timeout_seconds=60,
        sleep=lambda _seconds: None,
    )

    assert job == "projects/p/locations/r/jobs/promptopt-eval-project-digest"
    _, call = session.post_calls[0]
    template = call["json"]["template"]["template"]
    assert template["serviceAccount"] == "runner@p.iam.gserviceaccount.com"
    assert template["containers"][0]["image"] == image
    assert session.get_calls == ["https://run.googleapis.com/v2/projects/p/locations/r/operations/job-one"]


def test_materialization_produces_project_specific_protocol_12_identity(tmp_path, monkeypatch):
    source = b"source-archive"
    bundle = b"runtime-capsule"
    values = {"source.zip": source, "runtime.tar.gz": bundle}
    request = {
        "schema_version": 1,
        "project_id": "project-one",
        "source_object": "source.zip",
        "runtime_bundle_object": "runtime.tar.gz",
        "source_archive_sha256": hashlib.sha256(source).hexdigest(),
        "runtime_bundle_sha256": hashlib.sha256(bundle).hexdigest(),
        "base_runtime_image": f"repo/base@sha256:{'a' * 64}",
        "runtime_digest": "prepared-digest",
        "cloud_project_id": "control-project",
        "region": "asia-southeast1",
        "bucket": "bucket",
        "context_object": "runner-jobs/context.tar.gz",
        "image_repository": "repo/project-runtimes",
        "runner_service_account": "runner@control-project.iam.gserviceaccount.com",
        "build_service_account": "builder@control-project.iam.gserviceaccount.com",
        "model_project_id": "models",
        "coverup_model": "vertex_ai/model",
        "prepared_report": {
            "status": "runtime_ready",
            "protocol_version": 11,
            "projects": {"project-one": {"status": "ready"}},
            "runtime_digest": "prepared-digest",
            "runtime_image": f"repo/base@sha256:{'a' * 64}",
            "bundle_object": "runtime.tar.gz",
            "source_archive_sha256": hashlib.sha256(source).hexdigest(),
            "runtime_bundle_sha256": hashlib.sha256(bundle).hexdigest(),
        },
    }
    image = f"repo/project-runtimes/project-project-one@sha256:{'d' * 64}"
    worker = "projects/control-project/locations/asia-southeast1/jobs/promptopt-eval-project-one-digest"
    monkeypatch.setattr("cloud.runtime_image_factory._build_image", lambda *_args, **_kwargs: image)
    monkeypatch.setattr("cloud.runtime_image_factory._ensure_worker_job", lambda *_args, **_kwargs: worker)

    result = materialize_runtime(request, bucket=_Bucket(values), session=object(), root=tmp_path)

    assert result["status"] == "runtime_ready"
    assert result["protocol_version"] == 12
    assert result["runtime_image"] == image
    assert result["runtime_worker_job"] == worker
    expected_digest = hashlib.sha256(
        json.dumps(
            {
                "prepared_runtime": "prepared-digest",
                "source": hashlib.sha256(source).hexdigest(),
                "bundle": hashlib.sha256(bundle).hexdigest(),
                "image": image,
                "worker_job": worker,
                "runtime_protocol_version": 12,
                "execution_mode": "project_image",
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    assert result["runtime_digest"] == expected_digest
    assert "runner-jobs/context.tar.gz" in values


def test_materialization_rejects_a_cross_project_prepared_report(tmp_path):
    source = b"source"
    bundle = b"runtime"
    request = {
        "schema_version": 1,
        "project_id": "project-one",
        "source_object": "source.zip",
        "runtime_bundle_object": "runtime.tar.gz",
        "source_archive_sha256": hashlib.sha256(source).hexdigest(),
        "runtime_bundle_sha256": hashlib.sha256(bundle).hexdigest(),
        "base_runtime_image": f"repo/base@sha256:{'a' * 64}",
        "runtime_digest": "prepared-digest",
        "cloud_project_id": "control-project",
        "region": "asia-southeast1",
        "bucket": "bucket",
        "context_object": "context.tar.gz",
        "image_repository": "repo/project-runtimes",
        "runner_service_account": "runner@example.com",
        "build_service_account": "builder@example.com",
        "model_project_id": "models",
        "coverup_model": "model",
        "prepared_report": {
            "status": "runtime_ready",
            "protocol_version": 11,
            "projects": {"project-two": {}},
        },
    }

    with pytest.raises(RuntimeError, match="does not match the requested project"):
        materialize_runtime(
            request,
            bucket=_Bucket({"source.zip": source, "runtime.tar.gz": bundle}),
            session=object(),
            root=tmp_path,
        )
