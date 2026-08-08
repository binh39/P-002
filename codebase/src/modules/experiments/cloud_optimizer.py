import asyncio
import json
from uuid import uuid4

from .optimizer import OptimizationResult, OptimizationTarget
from .prompts import PromptBundle
from .schemas import ExperimentSettings


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
    ):
        self.client = client
        self.storage = storage
        self.bucket = bucket
        self.job_name = job_name
        self.timeout_seconds = timeout_seconds

    async def optimize(
        self,
        *,
        baseline: PromptBundle,
        train: list[OptimizationTarget],
        validation: list[OptimizationTarget],
        holdout: list[OptimizationTarget] | None,
        settings: ExperimentSettings,
    ) -> OptimizationResult:
        artifacts_prefix = await self.start(
            baseline=baseline,
            train=train,
            validation=validation,
            holdout=holdout,
            settings=settings,
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
        if settings.rate_limit:
            args.extend(["--rate-limit", str(settings.rate_limit)])
        if settings.pytest_args:
            args.extend(["--pytest-args", settings.pytest_args])
        request = {
            "name": self.job_name,
            "overrides": {
                "container_overrides": [
                    {
                        "args": args,
                        "env": [
                            {"name": "COVERUP_MODEL", "value": settings.coverup_model},
                            {"name": "OPTIMIZE_MODEL", "value": settings.optimize_model},
                        ],
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
            raise RuntimeError(f"Cloud Run GEPA job failed; missing artifacts: {missing}"[-4000:])

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
            },
        )
