"""Cloud Run adapter for user-requested final test generation.

This deliberately has a different GCS namespace and manifest from GEPA's
candidate-evaluation runner.  A TestGenerationRun can therefore expose only
the suite explicitly requested by a user.
"""

from __future__ import annotations

import asyncio
import json
from uuid import uuid4


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
            bundle_objects = {snapshot.runtime_bundle_object for snapshot in projects if snapshot.archive_object}
            if bundle_objects:
                if len(bundle_objects) != 1 or None in bundle_objects:
                    raise ValueError("Uploaded projects must share one prepared runtime bundle")
                source_bundle = bundle_objects.pop()
                copied_bundle = f"{prefix}/inputs/runtime.tar.gz"
                await self.storage.write(copied_bundle, await self.storage.read(source_bundle), "application/gzip")
                manifest_projects = []
                for snapshot in projects:
                    if not snapshot.archive_object:
                        continue
                    copied_archive = f"{prefix}/inputs/projects/{snapshot.runner_project}.zip"
                    await self.storage.write(
                        copied_archive,
                        await self.storage.read(snapshot.archive_object),
                        "application/zip",
                    )
                    manifest_projects.append(
                        {
                            "project": snapshot.runner_project,
                            "archive_object": copied_archive,
                            "source_directory": snapshot.source_directory,
                            "test_directory": snapshot.test_directory,
                        }
                    )
                if manifest_projects:
                    project_manifest_object = f"{prefix}/inputs/projects.json"
                    await self.storage.write(
                        project_manifest_object,
                        json.dumps(
                            {"projects": manifest_projects, "runtime_bundle_object": copied_bundle},
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
