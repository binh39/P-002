"""Cloud Run adapter for user-requested final test generation.

This deliberately has a different GCS namespace and manifest from GEPA's
candidate-evaluation runner.  A TestGenerationRun can therefore expose only
the suite explicitly requested by a user.
"""

from __future__ import annotations

import asyncio
import json
from uuid import uuid4


async def _object_generation(storage, object_name: str) -> str | None:
    getter = getattr(storage, "generation", None)
    if getter is None:
        return None
    try:
        value = await getter(object_name)
    except Exception:  # noqa: BLE001 - generation is optional for local fakes
        return None
    return str(value) if value is not None else None


class CloudRunJobTestGenerator:
    def __init__(self, *, client, storage, bucket: str, job_name: str, timeout_seconds: int):
        self.client = client
        self.storage = storage
        self.bucket = bucket
        self.job_name = job_name
        self.timeout_seconds = timeout_seconds

    async def start(
        self,
        *,
        prompt: dict[str, str],
        targets: list[dict[str, str]],
        model: str,
        settings: dict[str, int | float | str | None],
        projects: list | None = None,
        provider_secret_refs: dict[str, dict[str, str]] | None = None,
    ) -> str:
        if not targets:
            raise ValueError("Final test generation requires at least one target")
        execution_id = uuid4().hex
        prefix = f"runner-jobs/final-test-generation/{execution_id}"
        artifacts_prefix = f"{prefix}/artifacts"
        prompt_object = f"{prefix}/inputs/prompt.json"
        targets_object = f"{prefix}/inputs/targets.json"
        await self.storage.write(prompt_object, json.dumps(prompt, separators=(",", ":")).encode(), "application/json")
        await self.storage.write(
            targets_object, json.dumps(targets, separators=(",", ":")).encode(), "application/json"
        )

        project_manifest_object = None
        if projects:
            manifest_projects = []
            for snapshot in projects:
                if not snapshot.archive_object:
                    manifest_projects.append(
                        {
                            "kind": "sample",
                            "project": snapshot.runner_project,
                            "sample_slug": snapshot.project_id.split(":", 1)[-1],
                            "runtime_digest": snapshot.runtime_digest
                            or f"{snapshot.project_id}:{snapshot.commit or 'bundled'}",
                            "runtime_image": snapshot.runtime_image or "bundled-gepa-image",
                            "execution_mode": snapshot.runtime_execution_mode or "generic_worker_bundle",
                            "runtime_protocol_version": max(13, snapshot.runtime_protocol_version),
                            "python_version": snapshot.python_version,
                            "source_directory": snapshot.source_directory,
                            "test_directory": snapshot.test_directory,
                        }
                    )
                    continue
                if (
                    not snapshot.runtime_bundle_object
                    or not snapshot.runtime_digest
                    or not snapshot.runtime_worker_job
                    or not snapshot.source_archive_sha256
                    or not snapshot.runtime_bundle_sha256
                ):
                    raise ValueError(f"Uploaded project {snapshot.project_id} has no immutable runtime")
                copied_archive = f"{prefix}/inputs/projects/{snapshot.runner_project}.zip"
                copied_bundle = f"{prefix}/inputs/runtimes/{snapshot.runner_project}.tar.gz"
                await self.storage.write(
                    copied_archive,
                    await self.storage.read(snapshot.archive_object),
                    "application/zip",
                )
                await self.storage.write(
                    copied_bundle,
                    await self.storage.read(snapshot.runtime_bundle_object),
                    "application/gzip",
                )
                copied_archive_generation = await _object_generation(self.storage, copied_archive)
                copied_bundle_generation = await _object_generation(self.storage, copied_bundle)
                manifest_projects.append(
                    {
                        "kind": "uploaded",
                        "project": snapshot.runner_project,
                        "archive_object": copied_archive,
                        "runtime_bundle_object": copied_bundle,
                        "runtime_digest": snapshot.runtime_digest,
                        "runtime_image": snapshot.runtime_image,
                        "runtime_worker_job": snapshot.runtime_worker_job,
                        "execution_mode": snapshot.runtime_execution_mode or "generic_worker_bundle",
                        "runtime_protocol_version": snapshot.runtime_protocol_version,
                        "source_archive_sha256": snapshot.source_archive_sha256,
                        "runtime_bundle_sha256": snapshot.runtime_bundle_sha256,
                        "network_access": snapshot.network_access,
                        **(
                            {"source_archive_generation": copied_archive_generation}
                            if copied_archive_generation
                            else {}
                        ),
                        **(
                            {"runtime_bundle_generation": copied_bundle_generation}
                            if copied_bundle_generation
                            else {}
                        ),
                        "python_version": snapshot.python_version,
                        "source_directory": snapshot.source_directory,
                        "test_directory": snapshot.test_directory,
                    }
                )
            if manifest_projects:
                project_manifest_object = f"{prefix}/inputs/projects.json"
                await self.storage.write(
                    project_manifest_object,
                    json.dumps(
                        {"schema_version": 3, "projects": manifest_projects},
                        separators=(",", ":"),
                    ).encode(),
                    "application/json",
                )

        args = [
            "-m",
            "cloud.run_test_generation",
            "--bucket",
            self.bucket,
            "--artifacts-name",
            artifacts_prefix,
            "--prompt-object",
            prompt_object,
            "--targets-object",
            targets_object,
            "--model",
            model,
            "--max-attempts",
            str(settings["max_attempts"]),
            "--repeat-tests",
            str(settings["repeat_tests"]),
            "--max-concurrency",
            str(settings["max_concurrency"]),
            "--seed",
            str(settings["random_seed"]),
            "--evaluation-worker-timeout-seconds",
            str(self.timeout_seconds),
        ]
        if project_manifest_object:
            args.extend(["--project-manifest-object", project_manifest_object])
        if settings.get("rate_limit") is not None:
            args.extend(["--rate-limit", str(settings["rate_limit"])])
        if settings.get("pytest_args"):
            args.extend(["--pytest-args", str(settings["pytest_args"])])
        environment = [{"name": "COVERUP_MODEL", "value": model}]
        for name, reference in (provider_secret_refs or {}).items():
            environment.append(
                {
                    "name": name,
                    "value_source": {
                        "secret_key_ref": {"secret": reference["secret"], "version": reference["version"]}
                    },
                }
            )
        request = {
            "name": self.job_name,
            "overrides": {
                "container_overrides": [{"args": args, "env": environment}],
                "task_count": 1,
                "timeout": f"{self.timeout_seconds}s",
            },
        }
        try:
            await asyncio.to_thread(self.client.run_job, request=request)
        except Exception as exc:
            detail = str(exc).strip() or type(exc).__name__
            raise RuntimeError(f"Cloud Run test-generation job could not be started: {detail}"[-4000:]) from exc
        return artifacts_prefix

    async def collect(self, artifacts_prefix: str) -> dict | None:
        try:
            job = json.loads((await self.storage.read(f"{artifacts_prefix}/job_result.json")).decode())
        except Exception:
            return None
        if job.get("status") != "succeeded":
            missing = ", ".join(job.get("missing_artifacts", []))
            detail = str(job.get("error") or "").strip()
            raise RuntimeError(
                (
                    f"Cloud Run final test-generation job failed with exit code {job.get('return_code', 'unknown')}; "
                    f"missing artifacts: {missing or 'none'}"
                    f"{f'; {detail}' if detail else ''}"
                )[-4000:]
            )
        return json.loads((await self.storage.read(f"{artifacts_prefix}/test_generation_result.json")).decode())
