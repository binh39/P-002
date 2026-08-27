"""Materialize one prepared project capsule as an immutable OCI worker image."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import tarfile
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

_CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
_IMMUTABLE_IMAGE = re.compile(r"^[A-Za-z0-9._:/-]+@sha256:[0-9a-f]{64}$")
_TERMINAL_BUILD_STATES = {"SUCCESS", "FAILURE", "INTERNAL_ERROR", "TIMEOUT", "CANCELLED", "EXPIRED"}


def _digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


def _safe_token(value: str, *, length: int) -> str:
    normalized = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    return (normalized or "project")[:length].rstrip("-") or "project"


def _build_context(base_image: str, source_archive: Path, runtime_bundle: Path, destination: Path) -> None:
    if not _IMMUTABLE_IMAGE.fullmatch(base_image):
        raise RuntimeError("Runtime base image must be pinned by sha256 digest")
    dockerfile = (
        f"FROM {base_image}\n"
        "USER root\n"
        "RUN mkdir -p /opt/promptopt-project && chown appuser:appuser /opt/promptopt-project\n"
        "COPY --chown=appuser:appuser project.zip /opt/promptopt-project/project.zip\n"
        "COPY --chown=appuser:appuser runtime.tar.gz /opt/promptopt-project/runtime.tar.gz\n"
        "ENV PROMPTOPT_BAKED_SOURCE_ARCHIVE=/opt/promptopt-project/project.zip\n"
        "ENV PROMPTOPT_BAKED_RUNTIME_BUNDLE=/opt/promptopt-project/runtime.tar.gz\n"
        "USER appuser\n"
    ).encode()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(destination, "w:gz") as archive:
        info = tarfile.TarInfo("Dockerfile")
        info.size = len(dockerfile)
        info.mode = 0o644
        archive.addfile(info, io.BytesIO(dockerfile))
        archive.add(source_archive, arcname="project.zip", recursive=False)
        archive.add(runtime_bundle, arcname="runtime.tar.gz", recursive=False)


def _response_error(response: Any, operation: str) -> RuntimeError:
    detail = " ".join(str(getattr(response, "text", "")).split())[:2000]
    return RuntimeError(f"{operation} failed with HTTP {response.status_code}: {detail}")


def _poll_operation(
    session: Any,
    *,
    service: str,
    api_version: str,
    operation_name: str,
    deadline: float,
    sleep: Callable[[float], None],
) -> dict[str, Any]:
    while time.monotonic() < deadline:
        response = session.get(f"https://{service}/{api_version}/{operation_name}", timeout=30)
        if not 200 <= response.status_code < 300:
            raise _response_error(response, f"poll {operation_name}")
        payload = response.json()
        if payload.get("done"):
            if payload.get("error"):
                raise RuntimeError(
                    "Cloud operation failed: "
                    + " ".join(str(payload["error"].get("message") or payload["error"]).split())[:2000]
                )
            return payload
        sleep(2.0)
    raise TimeoutError(f"Cloud operation {operation_name} did not complete before its deadline")


def _build_image(
    session: Any,
    *,
    project_id: str,
    region: str,
    bucket_name: str,
    context_object: str,
    image_tag: str,
    timeout_seconds: int,
    build_service_account: str,
    sleep: Callable[[float], None],
) -> str:
    response = session.post(
        f"https://cloudbuild.googleapis.com/v1/projects/{project_id}/locations/{region}/builds",
        json={
            "source": {"storageSource": {"bucket": bucket_name, "object": context_object}},
            "steps": [
                {
                    "name": "gcr.io/cloud-builders/docker",
                    "args": ["build", "--pull", "--tag", image_tag, "."],
                }
            ],
            "images": [image_tag],
            "timeout": f"{timeout_seconds}s",
            "options": {"logging": "CLOUD_LOGGING_ONLY"},
            "serviceAccount": (
                f"projects/{project_id}/serviceAccounts/{build_service_account}"
                if not build_service_account.startswith("projects/")
                else build_service_account
            ),
        },
        timeout=30,
    )
    if not 200 <= response.status_code < 300:
        raise _response_error(response, "create Cloud Build")
    operation = response.json()
    operation_name = str(operation.get("name") or "")
    if not operation_name:
        raise RuntimeError("Cloud Build did not return an operation name")
    completed = _poll_operation(
        session,
        service="cloudbuild.googleapis.com",
        api_version="v1",
        operation_name=operation_name,
        deadline=time.monotonic() + timeout_seconds + 120,
        sleep=sleep,
    )
    build = completed.get("response") or {}
    status = str(build.get("status") or "")
    if status and status in _TERMINAL_BUILD_STATES and status != "SUCCESS":
        raise RuntimeError(f"Cloud Build finished with status {status}")
    images = (build.get("results") or {}).get("images") or []
    matching = next((item for item in images if item.get("name") == image_tag), images[0] if images else None)
    digest = str((matching or {}).get("digest") or "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise RuntimeError("Cloud Build did not publish an immutable image digest")
    return f"{image_tag.rsplit(':', 1)[0]}@{digest}"


def _ensure_worker_job(
    session: Any,
    *,
    project_id: str,
    region: str,
    job_id: str,
    image: str,
    runner_service_account: str,
    model_project_id: str,
    coverup_model: str,
    timeout_seconds: int,
    sleep: Callable[[float], None],
) -> str:
    parent = f"projects/{project_id}/locations/{region}"
    full_name = f"{parent}/jobs/{job_id}"
    environment = {
        "COVERUP_MODEL": coverup_model,
        "VERTEXAI_PROJECT": model_project_id,
        "VERTEXAI_LOCATION": "global",
        "PROMPTOPT_RUNTIME_IMAGE": image,
        "PROMPTOPT_RUNTIME_WORKER_JOB": full_name,
    }
    job = {
        "labels": {"promptopt-component": "project-evaluation-worker"},
        "template": {
            "parallelism": 1,
            "taskCount": 1,
            "template": {
                "serviceAccount": runner_service_account,
                "timeout": "7200s",
                "maxRetries": 0,
                "containers": [
                    {
                        "image": image,
                        "command": ["python"],
                        "args": ["-m", "cloud.run_evaluation_worker", "--help"],
                        "env": [{"name": name, "value": value} for name, value in environment.items()],
                        "resources": {"limits": {"cpu": "4", "memory": "8Gi"}},
                    }
                ],
            },
        },
    }
    response = session.post(
        f"https://run.googleapis.com/v2/{parent}/jobs",
        params={"jobId": job_id},
        json=job,
        timeout=30,
    )
    if response.status_code == 409:
        existing = session.get(f"https://run.googleapis.com/v2/{full_name}", timeout=30)
        if not 200 <= existing.status_code < 300:
            raise _response_error(existing, f"read existing worker {full_name}")
        containers = ((existing.json().get("template") or {}).get("template") or {}).get("containers") or []
        if not containers or containers[0].get("image") != image:
            raise RuntimeError(f"Existing worker {full_name} does not use the immutable project image")
        return full_name
    if not 200 <= response.status_code < 300:
        raise _response_error(response, f"create worker {full_name}")
    operation_name = str(response.json().get("name") or "")
    if not operation_name:
        raise RuntimeError("Cloud Run did not return a worker creation operation")
    _poll_operation(
        session,
        service="run.googleapis.com",
        api_version="v2",
        operation_name=operation_name,
        deadline=time.monotonic() + timeout_seconds,
        sleep=sleep,
    )
    return full_name


def materialize_runtime(
    request: dict[str, Any],
    *,
    bucket: Any,
    session: Any,
    root: Path,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    if request.get("schema_version") != 1:
        raise RuntimeError("Unsupported runtime-image request schema")
    prepared = request.get("prepared_report")
    if not isinstance(prepared, dict) or prepared.get("status") != "runtime_ready":
        raise RuntimeError("Runtime image factory requires a successful prepared runtime report")
    required = (
        "project_id",
        "source_object",
        "runtime_bundle_object",
        "source_archive_sha256",
        "runtime_bundle_sha256",
        "base_runtime_image",
        "runtime_digest",
        "cloud_project_id",
        "region",
        "bucket",
        "context_object",
        "image_repository",
        "runner_service_account",
        "build_service_account",
        "model_project_id",
        "coverup_model",
    )
    missing = [field for field in required if not request.get(field)]
    if missing:
        raise RuntimeError(f"Runtime image request is incomplete: {missing}")
    project_id_value = str(request["project_id"])
    if int(prepared.get("protocol_version") or 0) != 11:
        raise RuntimeError("Runtime image factory requires prepared capsule protocol 11")
    if set(prepared.get("projects") or {}) != {project_id_value}:
        raise RuntimeError("Prepared runtime does not match the requested project")
    prepared_identity = {
        "runtime_digest": prepared.get("runtime_digest"),
        "runtime_image": prepared.get("runtime_image"),
        "bundle_object": prepared.get("bundle_object"),
        "source_archive_sha256": prepared.get("source_archive_sha256"),
        "runtime_bundle_sha256": prepared.get("runtime_bundle_sha256"),
    }
    requested_identity = {
        "runtime_digest": request.get("runtime_digest"),
        "runtime_image": request.get("base_runtime_image"),
        "bundle_object": request.get("runtime_bundle_object"),
        "source_archive_sha256": request.get("source_archive_sha256"),
        "runtime_bundle_sha256": request.get("runtime_bundle_sha256"),
    }
    if prepared_identity != requested_identity:
        raise RuntimeError("Prepared runtime identity changed before image materialization")
    source = root / "project.zip"
    bundle = root / "runtime.tar.gz"
    bucket.blob(str(request["source_object"])).download_to_filename(str(source))
    bucket.blob(str(request["runtime_bundle_object"])).download_to_filename(str(bundle))
    if _digest(source) != request["source_archive_sha256"]:
        raise RuntimeError("Prepared source archive changed before image materialization")
    if _digest(bundle) != request["runtime_bundle_sha256"]:
        raise RuntimeError("Prepared runtime bundle changed before image materialization")

    project_id = str(request["cloud_project_id"])
    region = str(request["region"])
    project_token = _safe_token(str(request["project_id"]), length=18)
    digest_token = _safe_token(str(request["runtime_digest"]), length=20)
    image_tag = f"{request['image_repository']}/project-{project_token}:{digest_token}"
    context = root / "context.tar.gz"
    _build_context(str(request["base_runtime_image"]), source, bundle, context)
    context_object = str(request["context_object"])
    bucket.blob(context_object).upload_from_filename(str(context), content_type="application/gzip")
    immutable_image = _build_image(
        session,
        project_id=project_id,
        region=region,
        bucket_name=str(request["bucket"]),
        context_object=context_object,
        image_tag=image_tag,
        timeout_seconds=int(request.get("build_timeout_seconds", 1800)),
        build_service_account=str(request["build_service_account"]),
        sleep=sleep,
    )
    job_id = f"promptopt-eval-{project_token[:12]}-{digest_token[:12]}"
    worker_job = _ensure_worker_job(
        session,
        project_id=project_id,
        region=region,
        job_id=job_id,
        image=immutable_image,
        runner_service_account=str(request["runner_service_account"]),
        model_project_id=str(request["model_project_id"]),
        coverup_model=str(request["coverup_model"]),
        timeout_seconds=300,
        sleep=sleep,
    )
    final_digest = hashlib.sha256(
        json.dumps(
            {
                "prepared_runtime": request["runtime_digest"],
                "source": request["source_archive_sha256"],
                "bundle": request["runtime_bundle_sha256"],
                "image": immutable_image,
                "worker_job": worker_job,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return {
        **prepared,
        "status": "runtime_ready",
        "runtime_digest": final_digest,
        "runtime_image": immutable_image,
        "runtime_worker_job": worker_job,
        "protocol_version": 12,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--request-object", required=True)
    parser.add_argument("--result-object", required=True)
    args = parser.parse_args()
    from google.auth import default
    from google.auth.transport.requests import AuthorizedSession
    from google.cloud import storage

    credentials, _ = default(scopes=[_CLOUD_PLATFORM_SCOPE])
    session = AuthorizedSession(credentials)
    bucket = storage.Client().bucket(args.bucket)
    with tempfile.TemporaryDirectory(prefix="promptopt-runtime-image-") as temporary:
        root = Path(temporary)
        request_path = root / "request.json"
        bucket.blob(args.request_object).download_to_filename(str(request_path))
        request = json.loads(request_path.read_text(encoding="utf-8"))
        try:
            result = materialize_runtime(request, bucket=bucket, session=session, root=root)
            exit_code = 0
        except Exception as exc:  # noqa: BLE001 - factory must always publish a terminal result
            result = {
                "status": "runtime_failed",
                "error": f"Runtime image materialization failed: {exc}"[-4000:],
                "protocol_version": 12,
            }
            exit_code = 1
        bucket.blob(args.result_object).upload_from_string(
            json.dumps(result, ensure_ascii=False, indent=2),
            content_type="application/json",
        )
        print(json.dumps({"status": result["status"], "error": result.get("error")}), flush=True)
        return exit_code


if __name__ == "__main__":
    sys.exit(main())
