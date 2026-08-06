import asyncio
import json
from datetime import UTC, datetime
from functools import partial

from src.core.errors import AppError
from src.infrastructure.storage import ObjectStorage
from src.modules.analysis.repository import FunctionRepository
from src.modules.projects.service import ProjectService

from .dataset import split_targets
from .dispatcher import BaselineDispatcher, OptimizationDispatcher
from .executor import DockerCoverUpExecutor
from .optimizer import OptimizationTarget, optimize_prompt
from .prompts import baseline_prompt
from .repository import ExperimentRepository
from .schemas import (
    BaselineRunRecord,
    BaselineRunResponse,
    CreateExperimentRequest,
    ExperimentRecord,
    ExperimentResponse,
    ExperimentStatus,
    OptimizationRunRecord,
    OptimizationRunResponse,
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
        reflection_model: str = "",
        max_metric_calls: int = 30,
        allowed_reflection_models: set[str] | None = None,
    ):
        self.repository, self.projects, self.functions = repository, projects, functions
        self.storage, self.executor = storage, executor
        self.reflection_model = reflection_model
        self.max_metric_calls = max_metric_calls
        self.allowed_reflection_models = allowed_reflection_models or (
            {reflection_model} if reflection_model else set()
        )
        self.dispatcher: BaselineDispatcher | None = None
        self.optimization_dispatcher: OptimizationDispatcher | None = None

    def set_dispatcher(self, dispatcher: BaselineDispatcher) -> None:
        self.dispatcher = dispatcher

    def set_optimization_dispatcher(self, dispatcher: OptimizationDispatcher) -> None:
        self.optimization_dispatcher = dispatcher

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

    async def request_optimization(self, experiment_id: str, owner_id: str) -> OptimizationRunResponse:
        item = await self._owned(experiment_id, owner_id)
        if item.status != ExperimentStatus.BASELINE_SUCCEEDED:
            raise AppError(409, "BASELINE_NOT_READY", "A successful baseline is required before optimization")
        if not item.optimization_eligible:
            raise AppError(
                409,
                "OPTIMIZATION_DATASET_TOO_SMALL",
                "Optimization requires non-empty train, validation, and locked test splits",
            )
        if self.optimization_dispatcher is None:
            raise RuntimeError("Optimization dispatcher is not configured")
        baseline_run = await self.repository.get_run(item.baseline_run_id or "")
        if baseline_run is None or baseline_run.status != ExperimentStatus.BASELINE_SUCCEEDED:
            raise AppError(409, "BASELINE_NOT_READY", "The baseline result is unavailable")
        parent = baseline_prompt()
        if parent.digest() != baseline_run.prompt_digest:
            raise AppError(409, "BASELINE_PROMPT_CHANGED", "The baseline prompt version no longer matches this run")

        now = datetime.now(UTC)
        run = OptimizationRunRecord(
            id=new_id(),
            experiment_id=item.id,
            status=ExperimentStatus.OPTIMIZATION_QUEUED,
            parent_prompt_digest=parent.digest(),
            created_at=now,
        )
        await self.repository.create_optimization_run(run)
        item.status = ExperimentStatus.OPTIMIZATION_QUEUED
        item.optimization_run_id = run.id
        item.updated_at = now
        await self.repository.save(item)
        try:
            await self.optimization_dispatcher.dispatch(run.id)
        except Exception as exc:
            run.status = ExperimentStatus.FAILED
            run.error_message = "Optimization job could not be queued"
            run.finished_at = datetime.now(UTC)
            item.status = ExperimentStatus.BASELINE_SUCCEEDED
            item.optimization_run_id = None
            item.updated_at = run.finished_at
            await self.repository.save_optimization_run(run)
            await self.repository.save(item)
            raise AppError(503, "OPTIMIZATION_QUEUE_UNAVAILABLE", "Optimization could not be queued") from exc
        stored = await self.repository.get_optimization_run(run.id)
        return OptimizationRunResponse.model_validate(stored or run)

    async def get_optimization_run(self, run_id: str, owner_id: str) -> OptimizationRunResponse:
        run = await self.repository.get_optimization_run(run_id)
        if run is None:
            raise AppError(404, "OPTIMIZATION_RUN_NOT_FOUND", "Optimization run was not found")
        await self._owned(run.experiment_id, owner_id)
        return OptimizationRunResponse.model_validate(run)

    async def execute_optimization(self, run_id: str) -> None:
        run = await self.repository.get_optimization_run(run_id)
        if run is None or run.status != ExperimentStatus.OPTIMIZATION_QUEUED:
            return
        run.status = ExperimentStatus.OPTIMIZING
        run.started_at = datetime.now(UTC)
        await self.repository.save_optimization_run(run)
        item = await self.repository.get(run.experiment_id)
        try:
            if item is None or self.executor is None:
                raise RuntimeError("Optimization sandbox is not configured")
            if not self.reflection_model:
                raise RuntimeError("OPTIMIZE_MODEL is not configured")
            if (
                not self.reflection_model.startswith(("vertex_ai/", "gemini/"))
                or self.reflection_model not in self.allowed_reflection_models
            ):
                raise RuntimeError("OPTIMIZE_MODEL is not in the configured Gemini/Vertex allowlist")
            baseline_run = await self.repository.get_run(item.baseline_run_id or "")
            parent = baseline_prompt()
            if baseline_run is None or baseline_run.prompt_digest != parent.digest():
                raise RuntimeError("Baseline prompt version is unavailable or has changed")
            project = await self.projects.require_owned(item.project_id, item.owner_id)
            functions = {
                function_id: await self.functions.get(project.id, function_id)
                for function_id in item.target_function_ids
            }
            if any(function is None for function in functions.values()):
                raise RuntimeError("A selected function is no longer available")

            targets = {
                split: [
                    OptimizationTarget(
                        id=function_id,
                        symbol=functions[function_id].qualified_name,
                        source=functions[function_id].source,
                        split=split,
                    )
                    for function_id in item.dataset_splits[split]
                ]
                for split in ("train", "validation")
            }
            optimize = partial(
                optimize_prompt,
                executor=self.executor,
                archive=await self.storage.read(project.object_name),
                source_directory=project.settings.runtime.source_directory,
                baseline=parent,
                train=targets["train"],
                validation=targets["validation"],
                reflection_model=self.reflection_model,
                max_metric_calls=self.max_metric_calls,
            )
            result = await asyncio.to_thread(optimize)
            artifact_payloads = {
                "candidate_prompt.json": (result.candidate.as_json().encode(), "application/json"),
                "gepa_result.json": (
                    json.dumps(result.gepa_result, ensure_ascii=False, indent=2, default=str).encode(),
                    "application/json",
                ),
            }
            artifact_objects = {}
            for name, (content, content_type) in artifact_payloads.items():
                object_name = f"artifacts/{item.owner_id}/{item.project_id}/{item.id}/{run.id}/{name}"
                await self.storage.write(object_name, content, content_type)
                artifact_objects[name] = object_name
            run.status = ExperimentStatus.OPTIMIZATION_SUCCEEDED
            run.candidate_prompt = result.candidate.as_candidate()
            run.candidate_prompt_digest = result.candidate.digest()
            run.baseline_validation_score = result.baseline_score
            run.candidate_validation_score = result.score
            run.candidate_count = result.candidate_count
            run.metric_calls = result.metric_calls
            run.artifact_objects = artifact_objects
            run.finished_at = datetime.now(UTC)
            item.status = ExperimentStatus.OPTIMIZATION_SUCCEEDED
            item.updated_at = run.finished_at
        except Exception as exc:
            run.status = ExperimentStatus.FAILED
            run.error_message = str(exc)[-4000:]
            run.finished_at = datetime.now(UTC)
            if item:
                # A failed search does not invalidate the immutable baseline and may be retried.
                item.status = ExperimentStatus.BASELINE_SUCCEEDED
                item.updated_at = run.finished_at
        await self.repository.save_optimization_run(run)
        if item:
            await self.repository.save(item)

    async def _owned(self, experiment_id, owner_id):
        item = await self.repository.get(experiment_id)
        if item is None or item.owner_id != owner_id:
            raise AppError(404, "EXPERIMENT_NOT_FOUND", "Experiment was not found")
        return item
