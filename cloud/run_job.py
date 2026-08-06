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
import subprocess
import sys
from pathlib import Path


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--artifacts-name", required=True)
    parser.add_argument("--local-root", default="/app/artifacts")
    parser.add_argument("cli_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    cli_args = list(args.cli_args)
    if cli_args and cli_args[0] == "--":
        cli_args = cli_args[1:]

    local_dir = (Path(args.local_root) / args.artifacts_name).resolve()
    print(f"==> Artifacts will be written to {local_dir} (local disk)", flush=True)
    print(f"==> Upload target: gs://{args.bucket}/{args.artifacts_name}/", flush=True)

    command = [
        sys.executable, "-m", "src.optimization.cli",
        "--artifacts-dir", str(local_dir),
        *cli_args,
    ]
    print(f"==> Running: {' '.join(command)}", flush=True)
    return_code = subprocess.call(command)

    if local_dir.exists():
        try:
            print("==> Uploading results to GCS ...", flush=True)
            _upload_dir(args.bucket, args.artifacts_name, local_dir)
            print("==> Upload complete.", flush=True)
        except Exception as error:  # noqa: BLE001 - surface upload failures clearly
            print(f"==> ERROR: upload failed: {error}", file=sys.stderr, flush=True)
            return 1 if return_code == 0 else return_code
    else:
        print("==> No artifacts directory produced; nothing to upload.", flush=True)

    return return_code


if __name__ == "__main__":
    sys.exit(main())
