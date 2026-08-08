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
import io
import json
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


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


def _extract_archive(content: bytes, destination: Path, max_files: int, max_bytes: int) -> None:
    try:
        bundle = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as exc:
        raise RuntimeError("Project archive is not a valid ZIP") from exc
    entries = [entry for entry in bundle.infolist() if not entry.is_dir()]
    if len(entries) > max_files:
        raise RuntimeError("Project archive contains too many files")
    if sum(entry.file_size for entry in entries) > max_bytes:
        raise RuntimeError("Project archive exceeds the extraction limit")
    for entry in entries:
        path = PurePosixPath(entry.filename.replace("\\", "/"))
        mode = entry.external_attr >> 16
        if mode and stat.S_IFMT(mode) not in {0, stat.S_IFREG}:
            raise RuntimeError("Project archive contains a non-regular file")
        if path.is_absolute() or ".." in path.parts:
            raise RuntimeError("Project archive contains an unsafe path")
        target = (destination / path.as_posix()).resolve()
        if destination not in target.parents:
            raise RuntimeError("Project archive contains an unsafe path")
        target.parent.mkdir(parents=True, exist_ok=True)
        with bundle.open(entry) as source, target.open("wb") as output:
            shutil.copyfileobj(source, output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--artifacts-name", required=True)
    parser.add_argument("--local-root", default="/app/artifacts")
    parser.add_argument("--source-object")
    parser.add_argument("--dataset-object")
    parser.add_argument("--prompt-object")
    parser.add_argument("--project-layouts-object")
    parser.add_argument("--metric-calls", type=int, default=30)
    parser.add_argument("--evaluation-replicates", type=int, default=1)
    parser.add_argument("--max-concurrency", type=int, default=10)
    parser.add_argument("--repeat-tests", type=int, default=2)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--rate-limit", type=int)
    parser.add_argument("--pytest-args", default="")
    parser.add_argument("--reflection-temperature", type=float, default=0.7)
    parser.add_argument("--max-files", type=int, default=10_000)
    parser.add_argument("--max-uncompressed-bytes", type=int, default=100 * 1024 * 1024)
    parser.add_argument("cli_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    cli_args = list(args.cli_args)
    if cli_args and cli_args[0] == "--":
        cli_args = cli_args[1:]

    dynamic_values = (
        args.source_object,
        args.dataset_object,
        args.prompt_object,
        args.project_layouts_object,
    )
    dynamic_mode = any(dynamic_values)
    if dynamic_mode and not all(dynamic_values):
        parser.error("dynamic mode requires source, dataset, prompt, and project layouts")
    if dynamic_mode and args.artifacts_name.strip("/").startswith("prompt_optimization_v3"):
        parser.error("dynamic web runs may not write to the protected prompt_optimization_v3 prefix")

    with tempfile.TemporaryDirectory(prefix="promptopt-gepa-job-") as temporary:
        temporary_root = Path(temporary).resolve()
        local_dir = (
            (temporary_root / "artifacts").resolve()
            if dynamic_mode
            else (Path(args.local_root) / args.artifacts_name).resolve()
        )
        print(f"==> Artifacts will be written to {local_dir} (local disk)", flush=True)
        print(f"==> Upload target: gs://{args.bucket}/{args.artifacts_name}/", flush=True)

        if dynamic_mode:
            project = temporary_root / "project"
            source_archive = temporary_root / "source.zip"
            dataset = temporary_root / "dataset.jsonl"
            prompt = temporary_root / "prompt.json"
            layouts = temporary_root / "project-layouts.json"
            _download_object(args.bucket, args.source_object, source_archive)
            _download_object(args.bucket, args.dataset_object, dataset)
            _download_object(args.bucket, args.prompt_object, prompt)
            _download_object(args.bucket, args.project_layouts_object, layouts)
            project.mkdir()
            _extract_archive(source_archive.read_bytes(), project, args.max_files, args.max_uncompressed_bytes)
            layout_values = json.loads(layouts.read_text(encoding="utf-8"))
            if not layout_values:
                raise RuntimeError("At least one project layout is required")
            first = next(iter(layout_values.values()))
            package_dir = (project / first["package_dir"]).resolve()
            tests_dir = (project / first["tests_dir"]).resolve()
            for value in layout_values.values():
                for field in ("package_dir", "tests_dir"):
                    path = (project / value[field]).resolve()
                    if project not in path.parents or not path.is_dir():
                        raise RuntimeError(f"Configured {field} is absent from the archive")
            cli_args = [
                "--project-root",
                str(project),
                "--package-dir",
                str(package_dir),
                "--tests-dir",
                str(tests_dir),
                "--project-layouts",
                str(layouts),
                "--max-attempts",
                str(args.max_attempts),
                "--max-concurrency",
                str(args.max_concurrency),
                "--repeat-tests",
                str(args.repeat_tests),
            ]
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
            sys.executable,
            "-m",
            "src.optimization.cli",
            "--artifacts-dir",
            str(local_dir),
            *cli_args,
        ]
        print(f"==> Running: {' '.join(command)}", flush=True)
        return_code = subprocess.call(command)
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
                    "protocol_version": 1,
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
