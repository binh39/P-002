import asyncio
import json
from datetime import UTC, datetime, timedelta
from itertools import islice
from time import monotonic
from uuid import uuid4

from .evolution import CloudLogLine, parse_evolution_log
from .optimizer import OptimizationResult, OptimizationTarget
from .prompts import PromptBundle
from .schemas import EvolutionResponse, ExperimentSettings


class CloudRunJobGepaOptimizer:
    """Run Duy's full GEPA implementation in a dedicated Cloud Run Job.

    Every web run uses an opaque ``runner-jobs/gepa`` prefix in PromptOpt's private
    bucket. It never reads or writes the standalone benchmark prefix
    ``prompt_optimization_v3``.
    """

    def __init__(
        self,
        *,
        client,
        storage,
        bucket: str,
        job_name: str,
        timeout_seconds: int,
        logging_client=None,
        executions_client=None,
    ):
        self.client = client
        self.storage = storage
        self.bucket = bucket
        self.job_name = job_name
        self.timeout_seconds = timeout_seconds
        self.logging_client = logging_client
        self.executions_client = executions_client
        self._evolution_cache: dict[str, tuple[float, EvolutionResponse]] = {}

    async def optimize(
        self,
        *,
        baseline: PromptBundle,
        train: list[OptimizationTarget],
        validation: list[OptimizationTarget],
        holdout: list[OptimizationTarget] | None,
        settings: ExperimentSettings,
        vertexai_project: str | None = None,
        projects: list | None = None,
        provider_secret_refs: dict[str, dict[str, str]] | None = None,
    ) -> OptimizationResult:
        artifacts_prefix = await self.start(
            baseline=baseline,
            train=train,
            validation=validation,
            holdout=holdout,
            settings=settings,
            vertexai_project=vertexai_project,
            projects=projects,
            provider_secret_refs=provider_secret_refs,
        )
        result = await self.collect(artifacts_prefix)
        if result is None:
            raise RuntimeError("Cloud Run GEPA job has not published a result manifest")
        return result

    async def start(
        self,
        *,
        baseline: PromptBundle,
        train: list[OptimizationTarget],
        validation: list[OptimizationTarget],
        holdout: list[OptimizationTarget] | None,
        settings: ExperimentSettings,
        vertexai_project: str | None = None,
        projects: list | None = None,
        provider_secret_refs: dict[str, dict[str, str]] | None = None,
    ) -> str:
        """Upload immutable inputs and trigger the job without waiting for completion."""
        if not train or not validation:
            raise ValueError("GEPA requires non-empty train and validation splits")
        baseline.validate()
        execution_id = uuid4().hex
        prefix = f"runner-jobs/gepa/{execution_id}"
        artifacts_prefix = f"{prefix}/artifacts"
        dataset_object = f"{prefix}/inputs/dataset.jsonl"
        prompt_object = f"{prefix}/inputs/prompt.json"
        targets = [*train, *validation, *(holdout or [])]
        if any(not target.source_file for target in targets):
            raise ValueError("Cloud GEPA targets require analyzed source-file paths")
        dataset = "".join(
            json.dumps(
                {
                    "project": target.project,
                    "source_file": target.source_file,
                    "symbol": target.symbol,
                    "split": target.split,
                },
                separators=(",", ":"),
            )
            + "\n"
            for target in targets
        ).encode()
        await self.storage.write(dataset_object, dataset, "application/x-ndjson")
        await self.storage.write(prompt_object, baseline.as_json().encode(), "application/json")

        project_manifest_object = None
        if projects:
            manifest_projects = []
            bundle_objects = {snapshot.runtime_bundle_object for snapshot in projects if snapshot.archive_object}
            if len(bundle_objects) != 1 or None in bundle_objects:
                raise ValueError("Uploaded projects must share one prepared runtime bundle")
            source_bundle = bundle_objects.pop()
            copied_bundle = f"{prefix}/inputs/runtime.tar.gz"
            await self.storage.write(
                copied_bundle,
                await self.storage.read(source_bundle),
                "application/gzip",
            )
            for snapshot in projects:
                if not snapshot.archive_object:
                    continue
                copied_archive = f"{prefix}/inputs/projects/{snapshot.runner_project}.zip"
                archive = await self.storage.read(snapshot.archive_object)
                await self.storage.write(copied_archive, archive, "application/zip")
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
            "cloud.run_job",
            "--bucket",
            self.bucket,
            "--artifacts-name",
            artifacts_prefix,
            "--dataset-object",
            dataset_object,
            "--prompt-object",
            prompt_object,
            "--metric-calls",
            str(settings.max_metric_calls),
            "--evaluation-replicates",
            str(settings.evaluation_replicates),
            "--max-concurrency",
            str(settings.max_concurrency),
            "--repeat-tests",
            str(settings.repeat_tests),
            "--max-attempts",
            str(settings.max_attempts),
            "--reflection-temperature",
            str(settings.reflection_temperature),
        ]
        if project_manifest_object:
            args.extend(["--project-manifest-object", project_manifest_object])
        if settings.rate_limit:
            args.extend(["--rate-limit", str(settings.rate_limit)])
        if settings.pytest_args:
            args.extend(["--pytest-args", settings.pytest_args])
        environment = [
            {"name": "COVERUP_MODEL", "value": settings.coverup_model},
            {"name": "OPTIMIZE_MODEL", "value": settings.optimize_model},
        ]
        if vertexai_project:
            environment.append({"name": "VERTEXAI_PROJECT", "value": vertexai_project})
        for name, reference in (provider_secret_refs or {}).items():
            environment.append(
                {
                    "name": name,
                    "value_source": {
                        "secret_key_ref": {
                            "secret": reference["secret"],
                            "version": reference["version"],
                        }
                    },
                }
            )
        request = {
            "name": self.job_name,
            "overrides": {
                "container_overrides": [
                    {
                        "args": args,
                        "env": environment,
                    }
                ],
                "task_count": 1,
                "timeout": f"{self.timeout_seconds}s",
            },
        }
        try:
            await asyncio.to_thread(self.client.run_job, request=request)
        except Exception as exc:
            detail = str(exc).strip() or type(exc).__name__
            raise RuntimeError(f"Cloud Run GEPA job could not be started: {detail}"[-4000:]) from exc
        return artifacts_prefix

    async def collect(self, artifacts_prefix: str) -> OptimizationResult | None:
        """Return a completed result, or ``None`` while its manifest is absent."""
        try:
            manifest = json.loads((await self.storage.read(f"{artifacts_prefix}/job_result.json")).decode())
        except Exception:  # GCS NotFound means the job is still running.
            return None
        if manifest.get("status") != "succeeded":
            missing = ", ".join(manifest.get("missing_artifacts", []))
            return_code = manifest.get("return_code", "unknown")
            detail = str(manifest.get("error") or "").strip()
            raise RuntimeError(
                (
                    f"Cloud Run GEPA job failed with exit code {return_code}; "
                    f"missing artifacts: {missing or 'none'}"
                    f"{f'; {detail}' if detail else ''}"
                )[-4000:]
            )

        program = json.loads((await self.storage.read(f"{artifacts_prefix}/optimized_program.json")).decode())
        final_validation = json.loads((await self.storage.read(f"{artifacts_prefix}/final_validation.json")).decode())
        # ``gepa_optimized.json`` is the production decision and falls back to the
        # baseline when the proposal does not win.  The web comparison must retain
        # the actual proposal, which is always published separately.
        proposed_prompt = json.loads(
            (await self.storage.read(f"{artifacts_prefix}/prompts/gepa_proposed.json")).decode()
        )
        candidate = PromptBundle.from_candidate(proposed_prompt)
        candidate.validate()
        scores = [float(value) for value in program.get("validation_scores", [])]
        best_index = int(program.get("best_index", 0))
        score = scores[best_index] if 0 <= best_index < len(scores) else 0.0
        baseline_score = scores[0] if scores else 0.0
        try:
            cost_report = json.loads((await self.storage.read(f"{artifacts_prefix}/cost_report.json")).decode())
        except Exception:
            # Older jobs did not emit an accounting artifact and intentionally remain $0.
            cost_report = {"schema_version": 0, "total": {"estimated_cost_usd": 0.0}}
        return OptimizationResult(
            candidate=candidate,
            score=score,
            baseline_score=baseline_score,
            candidate_count=len(program.get("candidates", [])),
            metric_calls=int(program.get("total_metric_calls", 0)),
            gepa_result={
                "engine": "duyvu1105-cloud-run-gepa",
                "optimized_program": program,
                "final_validation": final_validation,
                "artifact_prefix": artifacts_prefix,
                "cost_report": cost_report,
            },
        )

    async def evolution(
        self,
        artifacts_prefix: str,
        *,
        started_at: datetime | None,
    ) -> EvolutionResponse:
        """Read this job execution's stdout and expose its GEPA iteration summary."""
        if self.logging_client is None:
            return EvolutionResponse(
                available=False,
                message="Cloud Logging is not configured for this API instance.",
            )
        cached = self._evolution_cache.get(artifacts_prefix)
        if cached and monotonic() - cached[0] < 5:
            return cached[1]
        try:
            entries = await asyncio.to_thread(
                self._read_execution_log,
                artifacts_prefix,
                started_at,
            )
        except Exception as exc:  # Logging must never break the optimization status API.
            detail = str(exc).strip() or type(exc).__name__
            return EvolutionResponse(
                available=False,
                message=f"Cloud Run logs are temporarily unavailable: {detail}"[:500],
            )
        result = parse_evolution_log(entries)
        if len(self._evolution_cache) >= 256:
            self._evolution_cache.pop(next(iter(self._evolution_cache)))
        self._evolution_cache[artifacts_prefix] = (monotonic(), result)
        return result

    async def cancel(
        self,
        artifacts_prefix: str,
        *,
        started_at: datetime | None,
    ) -> str:
        """Cancel the Cloud Run execution that owns an opaque artifact prefix."""
        if self.executions_client is None:
            raise RuntimeError("Cloud Run execution cancellation is not configured")
        execution_name = await asyncio.to_thread(
            self._resolve_execution_name,
            artifacts_prefix,
            started_at,
        )
        if not execution_name:
            raise RuntimeError("Cloud Run execution is not discoverable yet; retry in a few seconds")
        parts = self.job_name.split("/")
        full_name = f"projects/{parts[1]}/locations/{parts[3]}/jobs/{parts[-1]}/executions/{execution_name}"
        await asyncio.to_thread(
            self.executions_client.cancel_execution,
            request={"name": full_name},
        )
        return full_name

    def _resolve_execution_name(
        self,
        artifacts_prefix: str,
        started_at: datetime | None,
    ) -> str | None:
        if self.logging_client is None:
            return None
        execution_id = artifacts_prefix.strip("/").split("/")[-2]
        if not execution_id.isalnum():
            raise ValueError("Invalid Cloud Run artifact prefix")
        parts = self.job_name.split("/")
        project = parts[1]
        location = parts[3]
        job = parts[-1]
        earliest = (started_at or datetime.now(UTC)) - timedelta(minutes=5)
        timestamp_filter = earliest.astimezone(UTC).isoformat().replace("+00:00", "Z")
        base_filter = (
            'resource.type="cloud_run_job" '
            f'AND resource.labels.project_id="{project}" '
            f'AND resource.labels.location="{location}" '
            f'AND resource.labels.job_name="{job}" '
            f'AND timestamp>="{timestamp_filter}"'
        )
        marker_filter = f'{base_filter} AND textPayload:"{execution_id}"'
        marker_entries = list(
            islice(
                self.logging_client.list_entries(
                    filter_=marker_filter,
                    order_by="timestamp desc",
                    page_size=50,
                ),
                50,
            )
        )
        for entry in marker_entries:
            labels = getattr(entry, "labels", {}) or {}
            candidate = labels.get("run.googleapis.com/execution_name")
            payload = str(getattr(entry, "payload", ""))
            if candidate and execution_id in payload:
                return candidate
        return None

    def _read_execution_log(
        self,
        artifacts_prefix: str,
        started_at: datetime | None,
    ) -> list[CloudLogLine]:
        parts = self.job_name.split("/")
        project = parts[1]
        location = parts[3]
        job = parts[-1]
        earliest = (started_at or datetime.now(UTC)) - timedelta(minutes=5)
        timestamp_filter = earliest.astimezone(UTC).isoformat().replace("+00:00", "Z")
        base_filter = (
            'resource.type="cloud_run_job" '
            f'AND resource.labels.project_id="{project}" '
            f'AND resource.labels.location="{location}" '
            f'AND resource.labels.job_name="{job}" '
            f'AND timestamp>="{timestamp_filter}"'
        )
        execution_name = self._resolve_execution_name(artifacts_prefix, started_at)
        if not execution_name:
            return []
        execution_filter = f'{base_filter} AND labels."run.googleapis.com/execution_name"="{execution_name}"'
        cloud_entries = list(
            islice(
                self.logging_client.list_entries(
                    filter_=execution_filter,
                    order_by="timestamp asc",
                    page_size=1000,
                ),
                10_000,
            )
        )
        return [
            CloudLogLine(
                timestamp=getattr(entry, "timestamp", None),
                text=str(getattr(entry, "payload", "")),
            )
            for entry in cloud_entries
        ]
