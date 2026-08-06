from datetime import UTC, datetime

from src.core.errors import AppError
from src.infrastructure.storage import ObjectStorage
from src.modules.analysis.repository import FunctionRepository
from src.modules.projects.service import ProjectService

from .dataset import split_targets
from .dispatcher import BaselineDispatcher
from .executor import DockerCoverUpExecutor
from .prompts import baseline_prompt
from .repository import ExperimentRepository
from .schemas import (
    BaselineRunRecord,
    BaselineRunResponse,
    CreateExperimentRequest,
    ExperimentRecord,
    ExperimentResponse,
    ExperimentStatus,
    new_id,
)


class ExperimentService:
    def __init__(
        self,
        repository: ExperimentRepository,
        projects: ProjectService,
        functions: FunctionRepository,
        storage: ObjectStorage,
        executor: DockerCoverUpExecutor | None = None,
    ):
        self.repository, self.projects, self.functions = repository, projects, functions
        self.storage, self.executor = storage, executor
        self.dispatcher: BaselineDispatcher | None = None

    def set_dispatcher(self, dispatcher: BaselineDispatcher) -> None:
        self.dispatcher = dispatcher

    async def create(self, owner_id: str, payload: CreateExperimentRequest) -> ExperimentResponse:
        project = await self.projects.require_owned(payload.project_id, owner_id)
        if project.status not in {"ready", "warning"}:
            raise AppError(409, "ANALYSIS_NOT_READY", "Project analysis must finish before creating an experiment")
        available = {item.id for item in await self.functions.list_for_project(project.id)}
        if missing := set(payload.target_function_ids) - available:
            raise AppError(
                422, "UNKNOWN_TARGET_FUNCTION", f"Selected functions were not found: {', '.join(sorted(missing))}"
            )
        now = datetime.now(UTC)
        dataset_splits = split_targets(payload.target_function_ids)
        item = ExperimentRecord(
            id=new_id(),
            owner_id=owner_id,
            **payload.model_dump(),
            dataset_splits=dataset_splits,
            optimization_eligible=all(dataset_splits[name] for name in ("train", "validation", "test")),
            status=ExperimentStatus.DRAFT,
            created_at=now,
            updated_at=now,
        )
        await self.repository.create(item)
        return ExperimentResponse.model_validate(item)

    async def get(self, experiment_id: str, owner_id: str) -> ExperimentResponse:
        return ExperimentResponse.model_validate(await self._owned(experiment_id, owner_id))

    async def request_baseline(self, experiment_id: str, owner_id: str) -> BaselineRunResponse:
        item = await self._owned(experiment_id, owner_id)
        if item.status != ExperimentStatus.DRAFT:
            raise AppError(409, "BASELINE_ALREADY_REQUESTED", "A baseline run has already been requested")
        if self.dispatcher is None:
            raise RuntimeError("Baseline dispatcher is not configured")
        now = datetime.now(UTC)
        run = BaselineRunRecord(
            id=new_id(),
            experiment_id=item.id,
            status=ExperimentStatus.BASELINE_QUEUED,
            target_count=len(item.target_function_ids),
            created_at=now,
        )
        await self.repository.create_run(run)
        item.status, item.baseline_run_id, item.updated_at = ExperimentStatus.BASELINE_QUEUED, run.id, now
        await self.repository.save(item)
        try:
            await self.dispatcher.dispatch(run.id)
        except Exception as exc:
            run.status, run.error_message, run.finished_at = (
                ExperimentStatus.FAILED,
                "Baseline job could not be queued",
                datetime.now(UTC),
            )
            item.status, item.updated_at = ExperimentStatus.FAILED, run.finished_at
            await self.repository.save_run(run)
            await self.repository.save(item)
            raise AppError(503, "BASELINE_QUEUE_UNAVAILABLE", "Baseline run could not be queued") from exc
        return BaselineRunResponse.model_validate((await self.repository.get_run(run.id)) or run)

    async def get_run(self, run_id: str, owner_id: str) -> BaselineRunResponse:
        run = await self.repository.get_run(run_id)
        if run is None:
            raise AppError(404, "RUN_NOT_FOUND", "Baseline run was not found")
        await self._owned(run.experiment_id, owner_id)
        return BaselineRunResponse.model_validate(run)

    async def execute_baseline(self, run_id: str) -> None:
        run = await self.repository.get_run(run_id)
        if run is None:
            return
        run.status, run.started_at = ExperimentStatus.BASELINE_RUNNING, datetime.now(UTC)
        await self.repository.save_run(run)
        item = await self.repository.get(run.experiment_id)
        try:
            if item is None or self.executor is None:
                raise RuntimeError("Baseline sandbox is not configured")
            project = await self.projects.require_owned(item.project_id, item.owner_id)
            selected = [await self.functions.get(project.id, function_id) for function_id in item.target_function_ids]
            if any(function is None for function in selected):
                raise RuntimeError("A selected function is no longer available")
            prompt = baseline_prompt()
            result = await self.executor.execute(
                await self.storage.read(project.object_name),
                project.settings.runtime.source_directory,
                [function.qualified_name for function in selected if function],
                prompt,
            )
            artifact_objects = {}
            content_types = {
                "coverage_after.json": "application/json",
                "prompt.json": "application/json",
                "attempt_trace.jsonl": "application/x-ndjson",
                "generated_tests.zip": "application/zip",
                "target_coverage.json": "application/json",
            }
            for name, content in result.artifacts.items():
                object_name = f"artifacts/{item.owner_id}/{item.project_id}/{item.id}/{run.id}/{name}"
                await self.storage.write(object_name, content, content_types.get(name, "text/plain"))
                artifact_objects[name] = object_name
            (
                run.status,
                run.coverage_score,
                run.statement_coverage,
                run.branch_coverage,
                run.prompt_digest,
                run.artifact_objects,
                run.target_metrics,
                run.finished_at,
            ) = (
                ExperimentStatus.BASELINE_SUCCEEDED,
                result.coverage_score,
                result.statement_coverage,
                result.branch_coverage,
                prompt.digest(),
                artifact_objects,
                result.target_metrics,
                datetime.now(UTC),
            )
            item.status, item.updated_at = ExperimentStatus.BASELINE_SUCCEEDED, run.finished_at
        except Exception as exc:
            run.status, run.error_message, run.finished_at = (
                ExperimentStatus.FAILED,
                str(exc)[-4000:],
                datetime.now(UTC),
            )
            if item:
                item.status, item.updated_at = ExperimentStatus.FAILED, run.finished_at
        await self.repository.save_run(run)
        if item:
            await self.repository.save(item)

    async def _owned(self, experiment_id, owner_id):
        item = await self.repository.get(experiment_id)
        if item is None or item.owner_id != owner_id:
            raise AppError(404, "EXPERIMENT_NOT_FOUND", "Experiment was not found")
        return item
