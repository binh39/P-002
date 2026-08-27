"""Execute one project's GEPA metric request in its isolated runtime worker."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tarfile
import tempfile
import traceback
from pathlib import Path
from typing import Any

from cloud.runtime_workspace import (
    detect_layout,
    find_project_root,
    safe_extract_runtime_bundle,
    safe_extract_zip,
)
from src.optimization.models import ExperimentConfig, ProjectLayout, SymbolTarget
from src.optimization.runner import CoverUpExperimentRunner
from src.promptopt_pause import ModelRateLimitPauseError


def _download(bucket, object_name: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    bucket.blob(object_name).download_to_filename(str(destination))


def _safe_extract_checkpoint(archive_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            if member.issym() or member.islnk() or member.isdev():
                raise ValueError(f"Worker checkpoint contains unsupported entry: {member.name}")
            target = (root / member.name).resolve()
            if target != root and root not in target.parents:
                raise ValueError(f"Worker checkpoint escapes destination: {member.name}")
        archive.extractall(root, filter="data")


def _upload_checkpoint(bucket, object_name: str, artifacts: Path) -> None:
    archive_path = artifacts.parent / "checkpoint.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        if artifacts.is_dir():
            archive.add(artifacts, arcname=".", recursive=True)
    bucket.blob(object_name).upload_from_filename(
        str(archive_path),
        content_type="application/gzip",
    )


def _stage_project(bucket, request: dict[str, Any], root: Path) -> tuple[Path, ProjectLayout]:
    spec = request["project_spec"]
    name = str(request["project"])
    expected_image = str(spec.get("runtime_image") or "")
    worker_image = os.environ.get("PROMPTOPT_RUNTIME_IMAGE", "")
    if not expected_image or not worker_image:
        raise RuntimeError("Evaluation worker is missing its immutable runtime image identity")
    if expected_image != worker_image:
        raise RuntimeError("Runtime image changed after project admission; prepare the project runtime again")
    expected_job = str(spec.get("runtime_worker_job") or "")
    worker_job = os.environ.get("PROMPTOPT_RUNTIME_WORKER_JOB", "")
    if not expected_job or not worker_job:
        raise RuntimeError("Evaluation worker is missing its immutable Cloud Run job identity")
    if expected_job != worker_job:
        raise RuntimeError("Evaluation job changed after project admission; prepare the project runtime again")
    if spec.get("kind") == "sample":
        slug = str(spec.get("sample_slug") or name)
        source_root = Path(os.environ.get("PROMPTOPT_SAMPLE_REPOS_DIR", "/app/sample_repo")) / slug
        if not source_root.is_dir():
            raise RuntimeError(f"Evaluation worker does not contain sample project {slug!r}")
        project_root = root / "project"
        shutil.copytree(source_root, project_root)
        source, tests = detect_layout(
            project_root,
            str(spec.get("source_directory") or slug),
            str(spec.get("test_directory") or "tests"),
        )
        python = Path(sys.executable)
    else:
        required = (
            "archive_object",
            "runtime_bundle_object",
            "runtime_digest",
            "runtime_image",
            "runtime_worker_job",
            "source_archive_sha256",
            "runtime_bundle_sha256",
            "python_version",
        )
        missing = [field for field in required if not spec.get(field)]
        if missing:
            raise RuntimeError(f"Uploaded project runtime is incomplete: {missing}")
        expected_python = str(spec["python_version"])
        actual_python = f"{sys.version_info.major}.{sys.version_info.minor}"
        if expected_python != actual_python:
            raise RuntimeError(
                f"Evaluation worker Python {actual_python} does not match immutable runtime Python {expected_python}"
            )
        protocol_version = int(spec.get("runtime_protocol_version") or 1)
        if protocol_version >= 12:
            baked_archive = os.environ.get("PROMPTOPT_BAKED_SOURCE_ARCHIVE", "").strip()
            baked_bundle = os.environ.get("PROMPTOPT_BAKED_RUNTIME_BUNDLE", "").strip()
            if not baked_archive or not baked_bundle:
                raise RuntimeError("Project worker image does not contain its admitted source and runtime capsule")
            archive = Path(baked_archive)
            bundle = Path(baked_bundle)
            if not archive.is_file() or not bundle.is_file():
                raise RuntimeError("Project worker image contains incomplete baked runtime artifacts")
        else:
            archive = root / "project.zip"
            bundle = root / "runtime.tar.gz"
            _download(bucket, str(spec["archive_object"]), archive)
            _download(bucket, str(spec["runtime_bundle_object"]), bundle)
        expected_archive_hash = str(spec.get("source_archive_sha256") or "")
        expected_bundle_hash = str(spec.get("runtime_bundle_sha256") or "")
        if not expected_archive_hash or not expected_bundle_hash:
            raise RuntimeError("Immutable runtime manifest is missing content digests")
        if hashlib.sha256(archive.read_bytes()).hexdigest() != expected_archive_hash:
            raise RuntimeError("Uploaded project archive no longer matches its admitted runtime")
        if hashlib.sha256(bundle.read_bytes()).hexdigest() != expected_bundle_hash:
            raise RuntimeError("Project runtime bundle no longer matches its admitted runtime")
        python = safe_extract_runtime_bundle(bundle, root / "runtime")
        extracted = root / "source"
        safe_extract_zip(archive, extracted)
        project_root = find_project_root(extracted)
        source, tests = detect_layout(
            project_root,
            str(spec.get("source_directory") or "src"),
            str(spec.get("test_directory") or "tests"),
        )
    tests.mkdir(parents=True, exist_ok=True)
    import_root = source.parent if (source / "__init__.py").is_file() else source
    return project_root, ProjectLayout(
        package_dir=source,
        tests_dir=tests,
        import_root=import_root,
        python_executable=python,
        runtime_digest=str(spec.get("runtime_digest") or request.get("runtime_digest") or "sample"),
    )


def _execute(bucket, request: dict[str, Any], root: Path) -> dict[str, Any]:
    if request.get("schema_version") != 1:
        raise RuntimeError("Unsupported evaluation request schema")
    project = str(request["project"])
    project_root, layout = _stage_project(bucket, request, root)
    artifacts = root / "artifacts"
    checkpoint_object = str(request.get("checkpoint_object") or "")
    if checkpoint_object:
        checkpoint_blob = bucket.blob(checkpoint_object)
        if checkpoint_blob.exists():
            checkpoint = root / "checkpoint.tar.gz"
            checkpoint_blob.download_to_filename(str(checkpoint))
            _safe_extract_checkpoint(checkpoint, artifacts)
            os.environ["PROMPTOPT_RESUMING"] = "1"
    artifacts.mkdir(parents=True, exist_ok=True)
    pause_file = artifacts / "pause_signal.json"
    pause_file.unlink(missing_ok=True)
    os.environ["PROMPTOPT_PAUSE_FILE"] = str(pause_file)
    values = request["config"]
    config = ExperimentConfig(
        project_root=project_root,
        package_dir=layout.package_dir,
        tests_dir=layout.tests_dir,
        artifacts_dir=artifacts,
        coverup_model=str(values["coverup_model"]),
        max_attempts=int(values.get("max_attempts", 3)),
        repeat_tests=int(values.get("repeat_tests", 5)),
        max_concurrency=int(values.get("max_concurrency", 10)),
        rate_limit=values.get("rate_limit"),
        pytest_args=str(values.get("pytest_args", "")),
        projects={project: layout},
    )
    runner = CoverUpExperimentRunner(config)
    if request["operation"] == "batch":
        prompt = root / "prompt.json"
        _download(bucket, str(request["prompt_object"]), prompt)
        targets = [SymbolTarget.from_dict(item) for item in request["targets"]]
        record = runner.evaluate_batch(
            targets,
            prompt,
            candidate_id=str(request["candidate_id"]),
            split=str(request["split"]),
            workspace_kind=str(request.get("workspace_kind", "candidate")),
        )
        return {"record": record.as_dict()}
    if request["operation"] == "optimizer_test":
        result = runner.evaluate_optimizer_test(
            SymbolTarget.from_dict(request["target"]),
            str(request["test_module"]),
            experiment_id=str(request["experiment_id"]),
        )
        return {"optimizer_test": result}
    if request["operation"] == "final_generation":
        from cloud.run_test_generation import generate_local_project

        prompt = root / "final-prompt.json"
        _download(bucket, str(request["prompt_object"]), prompt)
        prompt_payload = json.loads(prompt.read_text(encoding="utf-8"))
        if set(prompt_payload) != {"initial", "error"} or not all(
            isinstance(value, str) for value in prompt_payload.values()
        ):
            raise RuntimeError("Final prompt snapshot must contain initial and error strings")
        targets = [SymbolTarget.from_dict(item) for item in request["targets"]]
        if not targets or {target.project for target in targets} != {project}:
            raise RuntimeError("Final-generation request crossed the project worker boundary")
        result = generate_local_project(
            artifacts=artifacts,
            prompt_path=prompt,
            targets=targets,
            config=config,
            sample_repos=project_root.parent,
            seed=int(request.get("seed", 7)),
        )
        (artifacts / "test_generation_result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        archive_path = Path(shutil.make_archive(str(root / "final-worker-artifacts"), "zip", root_dir=artifacts))
        artifact_object = str(request["artifact_object"])
        bucket.blob(artifact_object).upload_from_filename(str(archive_path), content_type="application/zip")
        return {"final_generation": result, "artifact_object": artifact_object}
    raise RuntimeError(f"Unsupported evaluation operation: {request['operation']!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--request-object", required=True)
    parser.add_argument("--result-object", required=True)
    args = parser.parse_args()
    from google.cloud import storage

    bucket = storage.Client().bucket(args.bucket)
    with tempfile.TemporaryDirectory(prefix="promptopt-evaluation-") as temporary:
        root = Path(temporary)
        request_path = root / "request.json"
        _download(bucket, args.request_object, request_path)
        request = json.loads(request_path.read_text(encoding="utf-8"))
        response: dict[str, Any] = {
            "schema_version": 1,
            "request_id": request.get("request_id"),
        }
        exit_code = 0
        try:
            response.update(_execute(bucket, request, root))
            response["status"] = "succeeded"
        except ModelRateLimitPauseError as exc:
            response.update(status="paused", error=str(exc)[-4000:])
            exit_code = 75
        except Exception as exc:  # noqa: BLE001 - terminal worker result must always be published
            detail = "".join(traceback.format_exception(exc))[-8000:]
            response.update(status="failed", error=detail)
            exit_code = 1
        finally:
            checkpoint_object = str(request.get("checkpoint_object") or "")
            artifacts = root / "artifacts"
            if checkpoint_object and artifacts.is_dir() and response.get("status") == "paused":
                _upload_checkpoint(bucket, checkpoint_object, artifacts)
            bucket.blob(args.result_object).upload_from_string(
                json.dumps(response, ensure_ascii=False, default=str),
                content_type="application/json",
            )
        print(
            json.dumps({"status": response.get("status"), "request_id": response.get("request_id")}),
            flush=True,
        )
        return exit_code


if __name__ == "__main__":
    sys.exit(main())
