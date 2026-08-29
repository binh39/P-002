"""Dispatch GEPA metric work to project-isolated Cloud Run workers.

The GEPA process remains the single search coordinator.  It never imports a
user project or executes its tests: each project group is sent to a worker
whose Python minor matches the immutable runtime prepared for that project.
Requests and results use GCS so a worker can outlive an HTTP connection and a
paused optimization can reuse its durable worker checkpoint.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.optimization.models import BatchRunRecord, EvaluationBackend, SymbolTarget
from src.promptopt_pause import ModelRateLimitPauseError, request_rate_limit_pause

_CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
_RESULT_POLL_SECONDS = 2.0


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class RemoteEvaluationBackend(EvaluationBackend):
    """Cloud Run implementation of the project evaluation boundary."""

    def __init__(
        self,
        *,
        bucket: str,
        artifact_prefix: str,
        manifest: dict[str, Any],
        jobs: dict[str, str],
        config: Any,
        timeout_seconds: int = 3600,
        storage_client: Any | None = None,
        authorized_session: Any | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if manifest.get("schema_version") not in (2, 3):
            raise ValueError("Remote evaluation requires project manifest schema 2 or 3")
        projects = manifest.get("projects")
        if not isinstance(projects, list) or not projects:
            raise ValueError("Remote evaluation manifest contains no projects")
        self.projects = {str(item["project"]): dict(item) for item in projects}
        if len(self.projects) != len(projects):
            raise ValueError("Remote evaluation manifest contains duplicate project names")
        self.bucket = bucket
        self.artifact_prefix = artifact_prefix.strip("/")
        self.jobs = {str(key): str(value) for key, value in jobs.items() if value}
        self.config = config
        self.timeout_seconds = timeout_seconds
        self._storage_client = storage_client
        self._authorized_session = authorized_session
        self._sleep = sleep

    @classmethod
    def from_environment(cls, config: Any) -> RemoteEvaluationBackend | None:
        manifest_path = os.environ.get("PROMPTOPT_EVALUATION_MANIFEST", "").strip()
        if not manifest_path:
            return None
        bucket = os.environ.get("PROMPTOPT_EVALUATION_BUCKET", "").strip()
        prefix = os.environ.get("PROMPTOPT_EVALUATION_PREFIX", "").strip()
        jobs_json = os.environ.get("PROMPTOPT_EVALUATION_JOBS", "").strip()
        if not bucket or not prefix or not jobs_json:
            raise RuntimeError(
                "Remote evaluation requires PROMPTOPT_EVALUATION_BUCKET, "
                "PROMPTOPT_EVALUATION_PREFIX and PROMPTOPT_EVALUATION_JOBS"
            )
        jobs = json.loads(jobs_json)
        if not isinstance(jobs, dict):
            raise RuntimeError("PROMPTOPT_EVALUATION_JOBS must be a JSON object")
        timeout = int(os.environ.get("PROMPTOPT_EVALUATION_TIMEOUT_SECONDS", "3600"))
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        return cls(
            bucket=bucket,
            artifact_prefix=prefix,
            manifest=manifest,
            jobs=jobs,
            config=config,
            timeout_seconds=timeout,
        )

    @property
    def storage_client(self):
        if self._storage_client is None:
            from google.cloud import storage

            self._storage_client = storage.Client()
        return self._storage_client

    @property
    def authorized_session(self):
        if self._authorized_session is None:
            import google.auth
            from google.auth.transport.requests import AuthorizedSession

            credentials, _ = google.auth.default(scopes=[_CLOUD_PLATFORM_SCOPE])
            self._authorized_session = AuthorizedSession(credentials)
        return self._authorized_session

    def _blob(self, object_name: str):
        return self.storage_client.bucket(self.bucket).blob(object_name)

    def _write_bytes(self, object_name: str, content: bytes, content_type: str) -> None:
        self._blob(object_name).upload_from_string(content, content_type=content_type)

    def _read_result(self, object_name: str) -> dict[str, Any] | None:
        blob = self._blob(object_name)
        if not blob.exists():
            return None
        value = json.loads(blob.download_as_bytes().decode("utf-8"))
        return value if isinstance(value, dict) else None

    def _job_for(self, project: dict[str, Any]) -> str:
        immutable_job = str(project.get("runtime_worker_job") or "").strip()
        if immutable_job:
            return immutable_job
        key = "sample" if project.get("kind") == "sample" else str(project.get("python_version", ""))
        job = self.jobs.get(key)
        if not job:
            raise RuntimeError(f"No independent evaluation worker is configured for {project['project']} ({key})")
        return job

    def _request_id(self, payload: dict[str, Any]) -> str:
        stable = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(stable.encode()).hexdigest()[:32]

    def _run_job(self, job_name: str, request_object: str, result_object: str) -> str | None:
        url = f"https://run.googleapis.com/v2/{job_name}:run"
        args = [
            "-m",
            "cloud.run_evaluation_worker",
            "--bucket",
            self.bucket,
            "--request-object",
            request_object,
            "--result-object",
            result_object,
        ]
        response = self.authorized_session.post(
            url,
            json={
                "overrides": {
                    "containerOverrides": [{"args": args}],
                    "taskCount": 1,
                    "timeout": f"{self.timeout_seconds}s",
                }
            },
            timeout=30,
        )
        if not 200 <= response.status_code < 300:
            detail = " ".join(response.text.split())[:2000]
            raise RuntimeError(f"Could not start independent evaluation worker ({response.status_code}): {detail}")
        try:
            operation = response.json()
        except (TypeError, ValueError):
            return None
        return str(operation.get("name") or "") or None

    def _operation_error(self, operation_name: str) -> str | None:
        response = self.authorized_session.get(
            f"https://run.googleapis.com/v2/{operation_name}",
            timeout=30,
        )
        if not 200 <= response.status_code < 300:
            return None
        try:
            operation = response.json()
        except (TypeError, ValueError):
            return None
        if not operation.get("done"):
            return None
        error = operation.get("error")
        if error:
            return " ".join(str(error.get("message") or error).split())[:2000]
        return "completed_without_result"

    def _submit(self, operation: str, project_name: str, body: dict[str, Any]) -> dict[str, Any]:
        try:
            project = self.projects[project_name]
        except KeyError as exc:
            raise RuntimeError(f"Project {project_name!r} is missing from evaluation manifest") from exc
        evaluation_config = {
            "coverup_model": self.config.coverup_model,
            "max_attempts": self.config.max_attempts,
            "repeat_tests": self.config.repeat_tests,
            "max_concurrency": self.config.max_concurrency,
            "rate_limit": self.config.rate_limit,
            "pytest_args": self.config.pytest_args,
        }
        identity = {
            "protocol": 1,
            "operation": operation,
            "project": project_name,
            "runtime_digest": project.get("runtime_digest") or f"sample:{project.get('sample_slug', project_name)}",
            "execution_mode": project.get("execution_mode", "generic_worker_bundle"),
            # A durable result may only be reused when the complete execution
            # protocol is identical.  Candidate IDs alone do not cover a
            # changed model, retry policy, pytest flags, or repeat count.
            "config": evaluation_config,
            **body,
        }
        request_id = self._request_id(identity)
        root = f"{self.artifact_prefix}/evaluation-workers/{project_name}/{request_id}"
        request_object = f"{root}/request.json"
        result_object = f"{root}/result.json"
        checkpoint_object = f"{root}/checkpoint.tar.gz"
        existing = self._read_result(result_object)
        expected_artifact = str(body.get("artifact_object") or "")
        if existing is not None and expected_artifact and not self._blob(expected_artifact).exists():
            # A terminal JSON result without its referenced immutable artifact
            # is incomplete, not a cache hit.  Re-run the same request.
            self._blob(result_object).delete()
            existing = None
        if existing is None or existing.get("status") == "paused":
            if existing is not None:
                self._blob(result_object).delete()
            request = {
                **identity,
                "schema_version": 1,
                "request_id": request_id,
                "project_spec": project,
                "checkpoint_object": checkpoint_object,
            }
            self._write_bytes(
                request_object,
                json.dumps(request, separators=(",", ":"), ensure_ascii=False).encode(),
                "application/json",
            )
            operation_name = self._run_job(self._job_for(project), request_object, result_object)
            deadline = time.monotonic() + self.timeout_seconds + 120
            completed_without_result = 0
            while time.monotonic() < deadline:
                existing = self._read_result(result_object)
                if existing is not None and existing.get("request_id") == request_id:
                    break
                if operation_name:
                    operation_error = self._operation_error(operation_name)
                    if operation_error == "completed_without_result":
                        completed_without_result += 1
                        if completed_without_result >= 3:
                            raise RuntimeError(
                                f"Evaluation worker for {project_name} completed without publishing a result"
                            )
                    elif operation_error:
                        raise RuntimeError(
                            f"Evaluation worker for {project_name} failed to start or execute: {operation_error}"
                        )
                self._sleep(_RESULT_POLL_SECONDS)
            else:
                raise TimeoutError(f"Evaluation worker for {project_name} did not publish a result in time")
        status = existing.get("status") if existing else None
        if status == "paused":
            error = ModelRateLimitPauseError(
                str(existing.get("error") or f"Evaluation worker for {project_name} paused")
            )
            # A remote worker owns the actual model call, but the coordinator
            # owns the durable Cloud Run execution state.  Forward the worker's
            # pause result to the coordinator signal file before bubbling the
            # exception so run_job.py can publish status=paused and resume from
            # the worker checkpoint on the next execution.
            request_rate_limit_pause(
                model=str(self.config.coverup_model),
                attempt=int(existing.get("attempt") or 1),
                error=error,
                force=True,
            )
            raise error
        if status != "succeeded":
            raise RuntimeError(str((existing or {}).get("error") or f"Evaluation worker for {project_name} failed"))
        return existing

    def _evaluate_project_batch(
        self,
        project: str,
        targets: list[SymbolTarget],
        prompt_template: Path,
        *,
        candidate_id: str,
        split: str,
        workspace_kind: str,
    ) -> BatchRunRecord:
        prompt_object = (
            f"{self.artifact_prefix}/evaluation-inputs/prompts/"
            f"{hashlib.sha256(prompt_template.read_bytes()).hexdigest()}.json"
        )
        self._write_bytes(prompt_object, prompt_template.read_bytes(), "application/json")
        result = self._submit(
            "batch",
            project,
            {
                "candidate_id": candidate_id,
                "split": split,
                "workspace_kind": workspace_kind,
                "prompt_object": prompt_object,
                "targets": [target.__dict__ for target in targets],
            },
        )
        return BatchRunRecord.from_dict(result["record"])

    def evaluate_batch(
        self,
        targets: list[SymbolTarget],
        prompt_template: Path,
        *,
        candidate_id: str | None,
        split: str | None,
        workspace_kind: str,
    ) -> BatchRunRecord:
        if not targets:
            raise ValueError("evaluate_batch requires at least one target")
        target_splits = {target.split for target in targets}
        if split is None:
            if len(target_splits) != 1:
                raise ValueError("Remote batch targets must share one split")
            split = next(iter(target_splits))
        elif target_splits != {split}:
            raise ValueError("Remote batch targets do not match the requested split")
        candidate_id = candidate_id or hashlib.sha256(prompt_template.read_bytes()).hexdigest()[:16]
        grouped: dict[str, list[SymbolTarget]] = {}
        for target in targets:
            grouped.setdefault(target.project, []).append(target)
        started_at = _utc_now()
        started = time.monotonic()
        with ThreadPoolExecutor(max_workers=min(len(grouped), max(1, self.config.max_concurrency))) as pool:
            futures = {
                project: pool.submit(
                    self._evaluate_project_batch,
                    project,
                    project_targets,
                    prompt_template,
                    candidate_id=candidate_id,
                    split=split,
                    workspace_kind=workspace_kind,
                )
                for project, project_targets in grouped.items()
            }
            records = {project: future.result() for project, future in futures.items()}
        results_by_identity = {
            (item.target.project, item.target.source_file, item.target.symbol, item.target.split): item
            for record in records.values()
            for item in record.results
        }
        ordered_results = []
        for target in targets:
            identity = (target.project, target.source_file, target.symbol, target.split)
            if identity not in results_by_identity:
                raise RuntimeError(f"Evaluation worker omitted target {identity}")
            ordered_results.append(results_by_identity[identity])
        return BatchRunRecord(
            run_id=f"remote-{split}-batch-{candidate_id[:24]}",
            split=split,
            targets=list(targets),
            command=["cloud-run-evaluation-worker", *sorted(grouped)],
            started_at=started_at,
            finished_at=_utc_now(),
            exit_code=next((record.exit_code for record in records.values() if record.exit_code), 0),
            elapsed_seconds=time.monotonic() - started,
            results=ordered_results,
            generated_tests=[
                f"{project}:{path}" for project, record in records.items() for path in record.generated_tests
            ],
            tests_workspace="remote-project-workers",
            stdout_file="",
            coverup_log_file="",
            attempt_trace_file="",
        )

    def evaluate_optimizer_test(
        self,
        target: SymbolTarget,
        test_module: str,
        *,
        experiment_id: str,
    ) -> dict[str, Any]:
        result = self._submit(
            "optimizer_test",
            target.project,
            {
                "experiment_id": experiment_id,
                "target": target.__dict__,
                "test_module": test_module,
            },
        )
        value = result.get("optimizer_test")
        if not isinstance(value, dict):
            raise RuntimeError("Evaluation worker returned an invalid optimizer-test result")
        return value

    def generate_final_project(
        self,
        project: str,
        targets: list[SymbolTarget],
        prompt_template: Path,
        *,
        seed: int,
    ) -> dict[str, Any]:
        """Generate a final suite on the immutable worker used for GEPA metrics."""
        if not targets or {target.project for target in targets} != {project}:
            raise ValueError("Final-generation targets must belong to exactly one project")
        prompt_digest = hashlib.sha256(prompt_template.read_bytes()).hexdigest()
        prompt_object = f"{self.artifact_prefix}/evaluation-inputs/prompts/{prompt_digest}.json"
        self._write_bytes(prompt_object, prompt_template.read_bytes(), "application/json")
        artifact_identity = self._request_id(
            {
                "project": project,
                "runtime": self.projects[project].get("runtime_digest"),
                "prompt": prompt_digest,
                "targets": [target.__dict__ for target in targets],
                "seed": seed,
            }
        )
        artifact_object = f"{self.artifact_prefix}/final-worker-artifacts/{project}/{artifact_identity}.zip"
        result = self._submit(
            "final_generation",
            project,
            {
                "prompt_object": prompt_object,
                "targets": [target.__dict__ for target in targets],
                "seed": seed,
                "artifact_object": artifact_object,
            },
        )
        value = result.get("final_generation")
        if not isinstance(value, dict):
            raise RuntimeError("Evaluation worker returned an invalid final-generation result")
        if int((value.get("metrics") or {}).get("test_file_count") or 0) <= 0:
            failures = value.get("generation_failures") or []
            detail = next(
                (
                    str(item.get("feedback") or "").strip()
                    for item in failures
                    if isinstance(item, dict) and item.get("feedback")
                ),
                "CoverUp did not retain a valid generated pytest module.",
            )
            raise RuntimeError(f"Final test generation produced no pytest modules: {detail}")
        artifact_sha256 = str(result.get("artifact_sha256") or "")
        if not re.fullmatch(r"[0-9a-f]{64}", artifact_sha256):
            raise RuntimeError("Evaluation worker returned no immutable final-suite artifact digest")
        replay_result = self._submit(
            "final_replay",
            project,
            {
                "suite_artifact_object": str(result.get("artifact_object") or artifact_object),
                "suite_artifact_sha256": artifact_sha256,
            },
        )
        replay = replay_result.get("final_replay")
        if not isinstance(replay, dict) or replay.get("status") != "passed":
            raise RuntimeError("Generated final-suite artifact failed its independent runtime replay")
        return {
            "result": value,
            "artifact_object": str(result.get("artifact_object") or artifact_object),
            "artifact_sha256": artifact_sha256,
            "replay": replay,
        }
