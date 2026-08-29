"""Cloud Run job wrapper for the GEPA/CoverUp pipeline.

Runs the CLI with artifacts on the container's LOCAL disk, then uploads the
results to GCS when the run finishes (successfully or not).

Why local: the pipeline writes sqlite coverage databases and uses random-access
writes, which Cloud Run's GCS volume mount (gcsfuse) cannot handle reliably
(OutOfOrderError / 503 retries / corrupted files).

Usage (as the job command):
    python -m cloud.run_job --bucket <bucket> --artifacts-name <name> -- <cli args...>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections import deque
from pathlib import Path

from cloud.runtime_workspace import _validate_project_id, detect_layout, find_project_root, safe_extract_zip


def _run_cli(command: list[str]) -> tuple[int, str | None]:
    """Stream CLI output to Cloud Logging with compact reflection diagnostics."""
    tail: deque[str] = deque(maxlen=200)
    child_env = os.environ.copy()
    child_env["PROMPTOPT_COMPACT_LOGS"] = "1"
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=child_env,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="", flush=True)
        tail.append(line.rstrip())
    return_code = process.wait()
    if return_code == 0:
        return return_code, None
    lines = list(tail)
    traceback_start = max((index for index, line in enumerate(lines) if line.startswith("Traceback")), default=-1)
    diagnostic = lines[traceback_start:] if traceback_start >= 0 else lines[-20:]
    detail = "\n".join(line for line in diagnostic if line.strip()).strip()
    return return_code, detail[-4000:] or f"Optimizer exited with code {return_code}"


def _upload_dir(bucket: str, prefix: str, local_dir: Path) -> None:
    """Recursively upload local_dir to gs://bucket/prefix/..., uploading sentinel manifest files last."""
    from google.cloud import storage  # installed via litellm[google]

    client = storage.Client()
    bucket_obj = client.bucket(bucket)
    all_files = [path for path in local_dir.rglob("*") if path.is_file()]
    regular_files = [path for path in all_files if path.name != "job_result.json"]
    sentinel_files = [path for path in all_files if path.name == "job_result.json"]
    files = regular_files + sentinel_files
    for index, path in enumerate(files, start=1):
        relative = path.relative_to(local_dir).as_posix()
        blob = bucket_obj.blob(f"{prefix}/{relative}" if prefix else relative)
        blob.upload_from_filename(str(path))
        if index % 50 == 0 or index == len(files):
            print(f"uploaded {index}/{len(files)} files", flush=True)


def _download_object(bucket: str, object_name: str, destination: Path) -> None:
    from google.cloud import storage

    destination.parent.mkdir(parents=True, exist_ok=True)
    storage.Client().bucket(bucket).blob(object_name).download_to_filename(str(destination))


def _download_verified(
    bucket: str,
    object_name: str,
    destination: Path,
    *,
    sha256: str | None = None,
    generation: str | None = None,
) -> None:
    from google.cloud import storage

    if generation:
        blob = storage.Client().bucket(bucket).blob(object_name)
        blob.reload()
        actual = getattr(blob, "generation", None)
        if actual is None or str(actual) != str(generation):
            raise RuntimeError(f"Runtime object generation changed for {object_name}")
    # Delegate the actual download so local/test adapters can provide an
    # in-memory object store without having to emulate google-cloud-storage.
    _download_object(bucket, object_name, destination)
    if sha256 and hashlib.sha256(destination.read_bytes()).hexdigest() != sha256:
        raise RuntimeError(f"Runtime source archive checksum changed for {object_name}")


def _download_dir(bucket: str, prefix: str, destination: Path) -> int:
    """Restore a previously uploaded artifact tree, excluding its terminal sentinel."""
    from google.cloud import storage

    normalized = prefix.strip("/")
    marker = normalized + "/"
    count = 0
    for blob in storage.Client().list_blobs(bucket, prefix=marker):
        relative = blob.name[len(marker) :]
        if not relative or relative in {"job_result.json", "pause_signal.json"}:
            continue
        target = destination / Path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(target))
        count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--artifacts-name", required=True)
    parser.add_argument("--local-root", default="/app/artifacts")
    parser.add_argument("--dataset-object")
    parser.add_argument("--prompt-object")
    parser.add_argument("--project-manifest-object")
    parser.add_argument("--resume-artifacts-name")
    parser.add_argument("--sample-repos-dir", default="/app/sample_repo")
    parser.add_argument("--metric-calls", type=int, default=30)
    parser.add_argument("--evaluation-replicates", type=int, default=1)
    parser.add_argument("--reflection-minibatch-size", type=int, choices=range(1, 6), default=5)
    parser.add_argument("--max-concurrency", type=int, default=10)
    parser.add_argument("--repeat-tests", type=int, default=5)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--rate-limit", type=int)
    parser.add_argument("--pytest-args", default="")
    parser.add_argument("--reflection-temperature", type=float, default=0.7)
    parser.add_argument("--pause-after-429", type=int, default=5)
    parser.add_argument("--evaluation-worker-timeout-seconds", type=int, default=3600)
    parser.add_argument("cli_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    cli_args = list(args.cli_args)
    if cli_args and cli_args[0] == "--":
        cli_args = cli_args[1:]

    dynamic_mode = bool(args.dataset_object or args.prompt_object)
    if dynamic_mode and not (args.dataset_object and args.prompt_object):
        parser.error("dynamic mode requires both --dataset-object and --prompt-object")
    if dynamic_mode and args.artifacts_name.strip("/").startswith("prompt_optimization_v3"):
        parser.error("dynamic web runs may not write to the protected prompt_optimization_v3 prefix")

    with tempfile.TemporaryDirectory(prefix="promptopt-gepa-job-") as temporary:
        managed_environment = (
            "PROMPTOPT_RESUMING",
            "PROMPTOPT_PAUSE_FILE",
            "PROMPTOPT_PAUSE_AFTER_429",
            "PROMPTOPT_EVALUATION_MANIFEST",
            "PROMPTOPT_EVALUATION_BUCKET",
            "PROMPTOPT_EVALUATION_PREFIX",
            "PROMPTOPT_EVALUATION_JOBS",
            "PROMPTOPT_EVALUATION_TIMEOUT_SECONDS",
        )
        previous_environment = {name: os.environ.get(name) for name in managed_environment}
        temporary_root = Path(temporary).resolve()
        local_dir = (
            temporary_root / "artifacts" if dynamic_mode else (Path(args.local_root) / args.artifacts_name).resolve()
        )
        print(f"==> Artifacts will be written to {local_dir} (local disk)", flush=True)
        print(f"==> Upload target: gs://{args.bucket}/{args.artifacts_name}/", flush=True)
        if args.resume_artifacts_name:
            restored = _download_dir(args.bucket, args.resume_artifacts_name, local_dir)
            os.environ["PROMPTOPT_RESUMING"] = "1"
            print(
                f"==> Restored {restored} checkpoint files from gs://{args.bucket}/{args.resume_artifacts_name}/",
                flush=True,
            )

        if dynamic_mode:
            sample_repos = Path(args.sample_repos_dir).resolve()
            dataset = temporary_root / "dataset.jsonl"
            prompt = temporary_root / "prompt.json"
            _download_object(args.bucket, args.dataset_object, dataset)
            _download_object(args.bucket, args.prompt_object, prompt)
            cli_python = Path(sys.executable)
            if args.project_manifest_object:
                manifest_path = temporary_root / "projects.json"
                _download_object(args.bucket, args.project_manifest_object, manifest_path)
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                projects = manifest.get("projects", [])
                if not projects or manifest.get("schema_version") not in (2, 3):
                    raise RuntimeError("Project GEPA requires an immutable-runtime manifest (schema 2 or 3)")
                worker_project = os.environ.get("PROMPTOPT_CLOUD_PROJECT", "").strip()
                worker_region = os.environ.get("PROMPTOPT_CLOUD_REGION", "").strip()
                worker_names = {
                    "sample": os.environ.get("PROMPTOPT_EVALUATION_JOB_SAMPLE", "").strip(),
                    "3.10": os.environ.get("PROMPTOPT_EVALUATION_JOB_PY310", "").strip(),
                    "3.11": os.environ.get("PROMPTOPT_EVALUATION_JOB_PY311", "").strip(),
                    "3.12": os.environ.get("PROMPTOPT_EVALUATION_JOB_PY312", "").strip(),
                    "3.13": os.environ.get("PROMPTOPT_EVALUATION_JOB_PY313", "").strip(),
                }
                relative_jobs = [name for name in worker_names.values() if name and not name.startswith("projects/")]
                if relative_jobs and (not worker_project or not worker_region):
                    raise RuntimeError(
                        "Independent evaluation worker names require PROMPTOPT_CLOUD_PROJECT and PROMPTOPT_CLOUD_REGION"
                    )
                worker_jobs = {
                    version: (
                        name
                        if name.startswith("projects/")
                        else f"projects/{worker_project}/locations/{worker_region}/jobs/{name}"
                    )
                    for version, name in worker_names.items()
                    if name
                }
                effective_manifest_path = local_dir / "execution_runtime_manifest.json"
                if args.resume_artifacts_name and effective_manifest_path.is_file():
                    effective_manifest = json.loads(effective_manifest_path.read_text(encoding="utf-8"))
                    if effective_manifest.get("schema_version") not in (2, 3):
                        raise RuntimeError("Saved execution runtime manifest is incompatible")
                    incoming_projects = {str(item["project"]): item for item in projects}
                    saved_projects = {str(item["project"]): item for item in effective_manifest.get("projects", [])}
                    if set(saved_projects) != set(incoming_projects):
                        raise RuntimeError("Resume project set differs from the immutable execution runtime manifest")
                    for project_name, saved in saved_projects.items():
                        incoming = incoming_projects[project_name]
                        for field in (
                            "kind",
                            "archive_object",
                            "runtime_bundle_object",
                            "source_archive_sha256",
                            "runtime_bundle_sha256",
                            "source_archive_generation",
                            "runtime_bundle_generation",
                            "runtime_digest",
                            "runtime_image",
                            "runtime_worker_job",
                            "runtime_protocol_version",
                            "execution_mode",
                            "python_version",
                        ):
                            if saved.get(field) != incoming.get(field):
                                raise RuntimeError(f"Resume project {project_name} changed immutable field {field}")
                    manifest = effective_manifest
                    projects = list(saved_projects.values())
                else:
                    sample_job = worker_jobs.get("sample", "")
                    sample_image = os.environ.get("PROMPTOPT_SAMPLE_RUNTIME_IMAGE", "").strip()
                    for project in projects:
                        if project.get("kind") != "sample":
                            continue
                        if not sample_job or not sample_image:
                            raise RuntimeError("Remote sample evaluation requires an immutable worker job and image")
                        base_digest = str(
                            project.get("runtime_digest") or f"sample:{project.get('sample_slug', project['project'])}"
                        )
                        project["runtime_worker_job"] = sample_job
                        project["runtime_image"] = sample_image
                        project["execution_mode"] = project.get("execution_mode") or "generic_worker_bundle"
                        project["runtime_protocol_version"] = 13
                        project["runtime_digest"] = hashlib.sha256(
                            json.dumps(
                                {
                                    "sample": base_digest,
                                    "image": sample_image,
                                    "worker_job": sample_job,
                                    "runtime_protocol_version": 13,
                                    "execution_mode": project["execution_mode"],
                                },
                                sort_keys=True,
                                separators=(",", ":"),
                            ).encode()
                        ).hexdigest()
                    manifest = {"schema_version": 3, "projects": projects}
                    effective_manifest_path.parent.mkdir(parents=True, exist_ok=True)
                    effective_manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
                # Remote workers consume the effective, execution-pinned
                # manifest rather than the mutable API input manifest.
                manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
                sample_repos = temporary_root / "sample_repos"
                project_layouts: dict[str, dict[str, str]] = {}
                for project in projects:
                    name = project["project"]
                    _validate_project_id(str(name))
                    if project.get("kind") == "sample":
                        slug = str(project.get("sample_slug") or name)
                        bundled_root = Path(args.sample_repos_dir).resolve() / slug
                        if not bundled_root.is_dir():
                            raise RuntimeError(f"Bundled sample repository is missing: {slug}")
                        destination = sample_repos / name
                        shutil.copytree(bundled_root, destination)
                        source, tests = detect_layout(
                            destination,
                            project.get("source_directory", slug),
                            project.get("test_directory", "tests"),
                        )
                        project_layouts[name] = {
                            "package_dir": str(source),
                            "tests_dir": str(tests),
                            "import_root": str(source.parent if (source / "__init__.py").is_file() else source),
                            "runtime_digest": str(project.get("runtime_digest") or f"sample:{slug}"),
                        }
                        continue
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
                    missing_fields = [field for field in required if not project.get(field)]
                    if missing_fields:
                        raise RuntimeError(
                            f"Uploaded project {name} has an incomplete immutable runtime: {missing_fields}"
                        )
                    archive = temporary_root / f"{name}.zip"
                    _download_verified(
                        args.bucket,
                        project["archive_object"],
                        archive,
                        sha256=(
                            project.get("source_archive_sha256")
                            if project.get("execution_mode") or int(project.get("runtime_protocol_version") or 1) >= 13
                            else None
                        ),
                        generation=project.get("source_archive_generation"),
                    )
                    extracted = temporary_root / "projects" / name
                    safe_extract_zip(archive, extracted)
                    project_root = find_project_root(extracted)
                    source, tests = detect_layout(
                        project_root,
                        project.get("source_directory", "src"),
                        project.get("test_directory", "tests"),
                    )
                    destination = sample_repos / name
                    shutil.copytree(project_root, destination)
                    staged_source = destination / source.relative_to(project_root)
                    staged_tests = destination / tests.relative_to(project_root)
                    # Runtime admission may intentionally select a synthetic
                    # empty test directory for projects that have no unit
                    # suite (or only executable integration harnesses).
                    staged_tests.mkdir(parents=True, exist_ok=True)
                    project_layout = {
                        "package_dir": str(staged_source),
                        "tests_dir": str(staged_tests),
                        "import_root": str(
                            staged_source.parent if (staged_source / "__init__.py").is_file() else staged_source
                        ),
                        "runtime_digest": str(project["runtime_digest"]),
                    }
                    project_layouts[name] = project_layout
                layouts_path = temporary_root / "project-layouts.json"
                layouts_path.write_text(
                    json.dumps(project_layouts, indent=2),
                    encoding="utf-8",
                )
                os.environ["PROMPTOPT_EVALUATION_MANIFEST"] = str(manifest_path)
                os.environ["PROMPTOPT_EVALUATION_BUCKET"] = args.bucket
                # Worker requests/results and checkpoints belong to the
                # original execution prefix.  A resumed coordinator writes a
                # new output prefix, but must continue using the old remote
                # prefix so an interrupted worker can restore its durable
                # checkpoint instead of starting from scratch.
                evaluation_prefix = args.resume_artifacts_name or args.artifacts_name
                os.environ["PROMPTOPT_EVALUATION_PREFIX"] = evaluation_prefix.strip("/")
                os.environ["PROMPTOPT_EVALUATION_JOBS"] = json.dumps(worker_jobs)
                os.environ["PROMPTOPT_EVALUATION_TIMEOUT_SECONDS"] = str(
                    max(300, min(args.evaluation_worker_timeout_seconds, 7200))
                )
            elif not sample_repos.is_dir():
                raise RuntimeError(f"Bundled sample repository directory is missing: {sample_repos}")
            cli_args = [
                "--project-root",
                "/app",
                "--package-dir",
                str(sample_repos / "isort" / "isort"),
                "--tests-dir",
                str(sample_repos / "isort" / "tests"),
                "--sample-repos-dir",
                str(sample_repos),
                "--max-attempts",
                str(args.max_attempts),
                "--max-concurrency",
                str(args.max_concurrency),
                "--repeat-tests",
                str(args.repeat_tests),
            ]
            if args.project_manifest_object:
                cli_args.extend(["--project-layouts-file", str(layouts_path)])
            if args.rate_limit:
                cli_args.extend(["--rate-limit", str(args.rate_limit)])
            if args.pytest_args:
                cli_args.extend(["--pytest-args", args.pytest_args])
            cli_args.extend(
                [
                    "optimize",
                    "--dataset",
                    str(dataset),
                    "--prompt",
                    str(prompt),
                    "--max-metric-calls",
                    str(args.metric_calls),
                    "--evaluation-replicates",
                    str(args.evaluation_replicates),
                    "--reflection-minibatch-size",
                    str(args.reflection_minibatch_size),
                    "--reflection-temperature",
                    str(args.reflection_temperature),
                ]
            )

        command = [
            str(cli_python) if dynamic_mode else sys.executable,
            "-u",
            "-m",
            "src.optimization.cli",
            "--artifacts-dir",
            str(local_dir),
            *cli_args,
        ]
        pause_path = local_dir / "pause_signal.json"
        pause_path.unlink(missing_ok=True)
        os.environ["PROMPTOPT_PAUSE_FILE"] = str(pause_path)
        os.environ["PROMPTOPT_PAUSE_AFTER_429"] = str(max(1, args.pause_after_429))
        print(f"==> Running: {' '.join(command)}", flush=True)
        try:
            return_code, cli_error = _run_cli(command)
        finally:
            for name, previous in previous_environment.items():
                if previous is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = previous
        local_dir.mkdir(parents=True, exist_ok=True)
        required = (
            "optimized_program.json",
            "prompts/gepa_proposed.json",
            "prompts/gepa_optimized.json",
            "final_validation.json",
        )
        missing = [name for name in required if not (local_dir / name).is_file()]
        pause_request = None
        if pause_path.is_file():
            try:
                pause_request = json.loads(pause_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pause_request = {"reason": "rate_limited", "message": "Model calls were rate limited"}
        status = (
            "paused" if pause_request is not None else ("succeeded" if return_code == 0 and not missing else "failed")
        )
        (local_dir / "job_result.json").write_text(
            json.dumps(
                {
                    "status": status,
                    "return_code": return_code,
                    "missing_artifacts": missing,
                    "protocol_version": 3,
                    "pause": pause_request,
                    "error": cli_error if status == "failed" else None,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        try:
            print("==> Uploading results to GCS ...", flush=True)
            _upload_dir(args.bucket, args.artifacts_name, local_dir)
            print("==> Upload complete.", flush=True)
        except Exception as error:  # noqa: BLE001 - surface upload failures clearly
            print(f"==> ERROR: upload failed: {error}", file=sys.stderr, flush=True)
            return 1
        return 0 if status in {"succeeded", "paused"} else (return_code or 1)


if __name__ == "__main__":
    sys.exit(main())
