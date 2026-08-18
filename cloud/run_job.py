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
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections import deque
from pathlib import Path

from cloud.runtime_workspace import detect_layout, find_project_root, safe_extract_runtime_bundle, safe_extract_zip


def _run_cli(command: list[str]) -> tuple[int, str | None]:
    """Stream CLI output to Cloud Logging while retaining a bounded traceback."""
    tail: deque[str] = deque(maxlen=200)
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
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
    """Recursively upload local_dir to gs://bucket/prefix/..."""
    from google.cloud import storage  # installed via litellm[google]

    client = storage.Client()
    bucket_obj = client.bucket(bucket)
    files = [path for path in local_dir.rglob("*") if path.is_file()]
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--artifacts-name", required=True)
    parser.add_argument("--local-root", default="/app/artifacts")
    parser.add_argument("--dataset-object")
    parser.add_argument("--prompt-object")
    parser.add_argument("--project-manifest-object")
    parser.add_argument("--sample-repos-dir", default="/app/sample_repo")
    parser.add_argument("--metric-calls", type=int, default=30)
    parser.add_argument("--evaluation-replicates", type=int, default=1)
    parser.add_argument("--max-concurrency", type=int, default=10)
    parser.add_argument("--repeat-tests", type=int, default=5)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--rate-limit", type=int)
    parser.add_argument("--pytest-args", default="")
    parser.add_argument("--reflection-temperature", type=float, default=0.7)
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
        temporary_root = Path(temporary).resolve()
        local_dir = (
            temporary_root / "artifacts" if dynamic_mode else (Path(args.local_root) / args.artifacts_name).resolve()
        )
        print(f"==> Artifacts will be written to {local_dir} (local disk)", flush=True)
        print(f"==> Upload target: gs://{args.bucket}/{args.artifacts_name}/", flush=True)

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
                if not projects or not manifest.get("runtime_bundle_object"):
                    raise RuntimeError("Uploaded-project GEPA requires projects and a prepared runtime bundle")
                bundle = temporary_root / "runtime.tar.gz"
                _download_object(args.bucket, manifest["runtime_bundle_object"], bundle)
                runtime_root = Path(os.environ.get("PROMPTOPT_RUNTIME_ROOT", "/tmp/promptopt-runtime"))
                if runtime_root.exists():
                    shutil.rmtree(runtime_root)
                runtime_python = safe_extract_runtime_bundle(bundle, runtime_root)
                sample_repos = temporary_root / "sample_repos"
                project_layouts: dict[str, dict[str, str]] = {}
                for project in projects:
                    name = project["project"]
                    archive = temporary_root / f"{name}.zip"
                    _download_object(args.bucket, project["archive_object"], archive)
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
                    project_layouts[name] = {
                        "package_dir": str(staged_source),
                        "tests_dir": str(staged_tests),
                        "import_root": str(
                            staged_source.parent if (staged_source / "__init__.py").is_file() else staged_source
                        ),
                    }
                layouts_path = temporary_root / "project-layouts.json"
                layouts_path.write_text(
                    json.dumps(project_layouts, indent=2),
                    encoding="utf-8",
                )
                os.environ["TESTGEN_PYTHON"] = str(runtime_python)
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
        print(f"==> Running: {' '.join(command)}", flush=True)
        return_code, cli_error = _run_cli(command)
        local_dir.mkdir(parents=True, exist_ok=True)
        required = (
            "optimized_program.json",
            "prompts/gepa_proposed.json",
            "prompts/gepa_optimized.json",
            "final_validation.json",
        )
        missing = [name for name in required if not (local_dir / name).is_file()]
        status = "succeeded" if return_code == 0 and not missing else "failed"
        (local_dir / "job_result.json").write_text(
            json.dumps(
                {
                    "status": status,
                    "return_code": return_code,
                    "missing_artifacts": missing,
                    "protocol_version": 2,
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
        return 0 if status == "succeeded" else (return_code or 1)


if __name__ == "__main__":
    sys.exit(main())
