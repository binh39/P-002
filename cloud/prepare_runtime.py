"""Cloud Run Job entry point for validating an uploaded Python project."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

from cloud.runtime_workspace import (
    RuntimeProjectSpec,
    RuntimeResult,
    create_runtime_bundle,
    prepare_environment,
)


def _prepare(args, bucket, root: Path) -> RuntimeResult:
    specs = []
    if args.manifest_object:
        manifest_path = root / "manifest.json"
        bucket.blob(args.manifest_object).download_to_filename(str(manifest_path))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        projects = manifest.get("projects", [])
    else:
        projects = [
            {
                "project_id": "project",
                "archive_object": args.archive_object,
                "source_directory": args.source_directory,
                "test_directory": args.test_directory,
            }
        ]
    for project in projects:
        archive = root / "archives" / f"{project['project_id']}.zip"
        archive.parent.mkdir(parents=True, exist_ok=True)
        bucket.blob(project["archive_object"]).download_to_filename(str(archive))
        specs.append(
            RuntimeProjectSpec(
                project["project_id"],
                archive,
                project.get("source_directory", "src"),
                project.get("test_directory", "tests"),
            )
        )
    runtime_root = Path(os.environ.get("PROMPTOPT_RUNTIME_ROOT", "/tmp/promptopt-runtime"))
    persistent_venv = runtime_root / ".venv"
    result, python = prepare_environment(
        specs,
        root / "workspace",
        timeout_seconds=args.timeout_seconds,
        maximum_output_bytes=args.maximum_output_bytes,
        expected_python=args.python_version,
        persistent_venv=persistent_venv,
    )
    if result.status == "runtime_ready" and python is not None:
        bundle = root / "runtime.tar.gz"
        create_runtime_bundle(persistent_venv, bundle)
        bucket.blob(args.bundle_object).upload_from_filename(
            str(bundle),
            content_type="application/gzip",
        )
        result.bundle_object = args.bundle_object
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--archive-object")
    parser.add_argument("--manifest-object")
    parser.add_argument("--result-object", required=True)
    parser.add_argument("--bundle-object", required=True)
    parser.add_argument("--source-directory", default="src")
    parser.add_argument("--test-directory", default="tests")
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--python-version", default="3.12")
    parser.add_argument("--maximum-output-bytes", type=int, default=10 * 1024 * 1024)
    args = parser.parse_args()
    if not args.manifest_object and not args.archive_object:
        parser.error("one of --manifest-object or --archive-object is required")
    from google.cloud import storage

    client = storage.Client()
    bucket = client.bucket(args.bucket)
    with tempfile.TemporaryDirectory(prefix="promptopt-runtime-") as temporary:
        root = Path(temporary)
        try:
            result = _prepare(args, bucket, root)
        except Exception as exc:  # noqa: BLE001 - always publish a terminal result
            result = RuntimeResult(
                status="runtime_failed",
                error=f"Runtime preparation could not complete: {exc}"[-4000:],
            )
        bucket.blob(args.result_object).upload_from_string(
            json.dumps(result.as_dict(), ensure_ascii=False, indent=2),
            content_type="application/json",
        )
        print(json.dumps({"status": result.status, "error": result.error}), flush=True)
        return 0 if result.status == "runtime_ready" else 1


if __name__ == "__main__":
    sys.exit(main())
