import asyncio
import json
from uuid import uuid4

from .executor import BaselineExecution
from .prompts import PromptBundle
from .schemas import ExperimentSettings


class CloudRunJobCoverUpExecutor:
    """Executes one CoverUp evaluation in an isolated Cloud Run Job task."""

    def __init__(self, *, client, storage, bucket: str, job_name: str, timeout_seconds: int):
        self.client = client
        self.storage = storage
        self.bucket = bucket
        self.job_name = job_name
        self.timeout_seconds = timeout_seconds
        self.image = job_name
        self.memory_mb = 2048
        self.cpu = 1
        self.network_mode = "cloud-run-job"

    async def execute(
        self,
        archive: bytes,
        source_directory: str,
        symbols: list[str],
        prompt: PromptBundle,
        settings: ExperimentSettings | None = None,
    ) -> BaselineExecution:
        prompt.validate()
        settings = settings or ExperimentSettings()
        execution_id = uuid4().hex
        prefix = f"runner-jobs/{execution_id}"
        spec = {
            "protocol_version": 1,
            "source_directory": source_directory,
            "symbols": symbols,
            "prompt_digest": prompt.digest(),
            "settings": settings.model_dump(),
        }
        await self.storage.write(f"{prefix}/source.zip", archive, "application/zip")
        await self.storage.write(f"{prefix}/prompt.json", prompt.as_json().encode(), "application/json")
        await self.storage.write(
            f"{prefix}/spec.json",
            json.dumps(spec, separators=(",", ":")).encode(),
            "application/json",
        )
        request = {
            "name": self.job_name,
            "overrides": {
                "container_overrides": [
                    {
                        "env": [
                            {"name": "PROMPTOPT_JOB_BUCKET", "value": self.bucket},
                            {"name": "PROMPTOPT_JOB_PREFIX", "value": prefix},
                            {"name": "COVERUP_MODEL", "value": settings.coverup_model},
                        ]
                    }
                ],
                "task_count": 1,
                "timeout": f"{self.timeout_seconds}s",
            },
        }
        operation_error = None

        def run_job_and_wait():
            operation = self.client.run_job(request=request)
            return operation.result(timeout=self.timeout_seconds + 60)

        try:
            await asyncio.to_thread(run_job_and_wait)
        except TimeoutError as exc:
            raise RuntimeError("Cloud Run Job evaluation timed out") from exc
        except Exception as exc:
            operation_error = exc
        try:
            result = json.loads((await self.storage.read(f"{prefix}/result.json")).decode())
        except Exception as exc:
            if operation_error:
                detail = str(operation_error).strip() or type(operation_error).__name__
                raise RuntimeError(
                    f"Cloud Run Job failed before publishing a result manifest: {detail}"[-4000:]
                ) from operation_error
            raise RuntimeError("Cloud Run Job did not publish a valid result manifest") from exc
        if result.get("status") != "succeeded":
            raise RuntimeError(str(result.get("error") or "Cloud Run Job evaluation failed")[-4000:])
        artifacts = {
            name: await self.storage.read(f"{prefix}/artifacts/{name}") for name in result.get("artifacts", [])
        }
        return BaselineExecution(
            coverage_score=result.get("coverage_score"),
            statement_coverage=result.get("statement_coverage"),
            branch_coverage=result.get("branch_coverage"),
            artifacts=artifacts,
            target_metrics=result.get("target_metrics", {}),
        )
