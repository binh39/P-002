import asyncio
import json
from datetime import UTC, datetime
from functools import partial

from src.core.errors import AppError
from src.infrastructure.storage import ObjectStorage
from src.modules.analysis.repository import FunctionRepository
from src.modules.projects.samples import SampleProjectCatalog
from src.modules.projects.service import ProjectService

from .comparison import compare_prompts
from .dataset import split_targets
from .dispatcher import BaselineDispatcher, ComparisonDispatcher, OptimizationDispatcher
from .executor import DockerCoverUpExecutor
from .optimizer import OptimizationTarget, optimize_prompt
from .prompts import PromptBundle, baseline_prompt
from .repository import ExperimentRepository
from .schemas import (
    BaselineRunRecord,
    BaselineRunResponse,
    ComparisonRunRecord,
    ComparisonRunResponse,
    CreateExperimentRequest,
    ExperimentListResponse,
    ExperimentRecord,
    ExperimentResponse,
    ExperimentStatus,
    OptimizationRunRecord,
    OptimizationRunResponse,
    PromptVersionListResponse,
    PromptVersionRecord,
    PromptVersionResponse,
    PromptVersionStatus,
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
        final_evaluation_replicates: int = 2,
        cloud_optimizer=None,
        samples: SampleProjectCatalog | None = None,
    ):
        self.repository, self.projects, self.functions = repository, projects, functions
        self.storage, self.executor = storage, executor
        self.reflection_model = reflection_model
        self.max_metric_calls = max_metric_calls
        self.allowed_reflection_models = allowed_reflection_models or (
            {reflection_model} if reflection_model else set()
        )
        self.final_evaluation_replicates = final_evaluation_replicates
        self.cloud_optimizer = cloud_optimizer
        self.samples = samples
        self.dispatcher: BaselineDispatcher | None = None
        self.optimization_dispatcher: OptimizationDispatcher | None = None
        self.comparison_dispatcher: ComparisonDispatcher | None = None

    def set_dispatcher(self, dispatcher: BaselineDispatcher) -> None:
        self.dispatcher = dispatcher

    def set_optimization_dispatcher(self, dispatcher: OptimizationDispatcher) -> None:
        self.optimization_dispatcher = dispatcher

    def set_comparison_dispatcher(self, dispatcher: ComparisonDispatcher) -> None:
        self.comparison_dispatcher = dispatcher

    async def create(self, owner_id: str, payload: CreateExperimentRequest) -> ExperimentResponse:
        project = await self.projects.require_owned(payload.project_id, owner_id)
        if project.status not in {"ready", "warning"}:
            raise AppError(409, "ANALYSIS_NOT_READY", "Project analysis must finish before creating an experiment")
        available = {item.id for item in await self._list_functions(project.id)}
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

    async def list(self, owner_id: str) -> ExperimentListResponse:
        items = await self.repository.list_for_owner(owner_id)
        return ExperimentListResponse(
            items=[ExperimentResponse.model_validate(item) for item in items],
            total=len(items),
        )

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

    async def get_baseline_artifact(self, run_id: str, artifact_name: str, owner_id: str) -> bytes:
        run = await self.repository.get_run(run_id)
        if run is None:
            raise AppError(404, "RUN_NOT_FOUND", "Baseline run was not found")
        await self._owned(run.experiment_id, owner_id)
        object_name = run.artifact_objects.get(artifact_name)
        if object_name is None:
            raise AppError(404, "ARTIFACT_NOT_FOUND", "Baseline artifact was not found")
        return await self.storage.read(object_name)

    async def execute_baseline(self, run_id: str) -> None:
        run = await self.repository.get_run(run_id)
        if run is None or run.status != ExperimentStatus.BASELINE_QUEUED:
            return
        run.status, run.started_at = ExperimentStatus.BASELINE_RUNNING, datetime.now(UTC)
        await self.repository.save_run(run)
        item = await self.repository.get(run.experiment_id)
        try:
            if item is None or self.executor is None:
                raise RuntimeError("Baseline sandbox is not configured")
            project = await self.projects.require_owned(item.project_id, item.owner_id)
            selected = [await self._get_function(project.id, function_id) for function_id in item.target_function_ids]
            if any(function is None for function in selected):
                raise RuntimeError("A selected function is no longer available")
            prompt = baseline_prompt()
            result = await self.executor.execute(
                await self._read_project_archive(project),
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

    async def get_optimization_artifact(self, run_id: str, artifact_name: str, owner_id: str) -> bytes:
        run = await self.repository.get_optimization_run(run_id)
        if run is None:
            raise AppError(404, "OPTIMIZATION_RUN_NOT_FOUND", "Optimization run was not found")
        await self._owned(run.experiment_id, owner_id)
        object_name = run.artifact_objects.get(artifact_name)
        if object_name is None:
            raise AppError(404, "ARTIFACT_NOT_FOUND", "Optimization artifact was not found")
        return await self.storage.read(object_name)

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
                function_id: await self._get_function(project.id, function_id)
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
                        source_file=getattr(functions[function_id], "file", ""),
                    )
                    for function_id in item.dataset_splits[split]
                ]
                for split in ("train", "validation")
            }
            archive = await self._read_project_archive(project)
            if self.cloud_optimizer is not None:
                holdout = [
                    OptimizationTarget(
                        id=function_id,
                        symbol=functions[function_id].qualified_name,
                        source=functions[function_id].source,
                        split="test",
                        source_file=getattr(functions[function_id], "file", ""),
                    )
                    for function_id in item.dataset_splits["test"]
                ]
                result = await self.cloud_optimizer.optimize(
                    archive=archive,
                    source_directory=project.settings.runtime.source_directory,
                    baseline=parent,
                    train=targets["train"],
                    validation=targets["validation"],
                    holdout=holdout,
                    reflection_model=self.reflection_model,
                    max_metric_calls=self.max_metric_calls,
                )
            else:
                optimize = partial(
                    optimize_prompt,
                    executor=self.executor,
                    archive=archive,
                    source_directory=project.settings.runtime.source_directory,
                    baseline=parent,
                    train=targets["train"],
                    validation=targets["validation"],
                    holdout=None,
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

    async def request_comparison(self, experiment_id: str, owner_id: str) -> ComparisonRunResponse:
        item = await self._owned(experiment_id, owner_id)
        if item.status != ExperimentStatus.OPTIMIZATION_SUCCEEDED:
            raise AppError(409, "OPTIMIZATION_NOT_READY", "A successful optimization is required before comparison")
        if self.comparison_dispatcher is None:
            raise RuntimeError("Comparison dispatcher is not configured")
        optimization = await self.repository.get_optimization_run(item.optimization_run_id or "")
        if (
            optimization is None
            or optimization.status != ExperimentStatus.OPTIMIZATION_SUCCEEDED
            or not optimization.candidate_prompt
            or not optimization.candidate_prompt_digest
        ):
            raise AppError(409, "OPTIMIZATION_NOT_READY", "The locked candidate prompt is unavailable")
        now = datetime.now(UTC)
        run = ComparisonRunRecord(
            id=new_id(),
            experiment_id=item.id,
            optimization_run_id=optimization.id,
            status=ExperimentStatus.COMPARISON_QUEUED,
            baseline_prompt_digest=optimization.parent_prompt_digest,
            candidate_prompt_digest=optimization.candidate_prompt_digest,
            test_target_ids=list(item.dataset_splits.get("test", [])),
            replicate_count=self.final_evaluation_replicates,
            created_at=now,
        )
        if not run.test_target_ids:
            raise AppError(409, "LOCKED_TEST_SPLIT_EMPTY", "The experiment has no locked test targets")
        await self.repository.create_comparison_run(run)
        item.status = ExperimentStatus.COMPARISON_QUEUED
        item.comparison_run_id = run.id
        item.updated_at = now
        await self.repository.save(item)
        try:
            await self.comparison_dispatcher.dispatch(run.id)
        except Exception as exc:
            run.status = ExperimentStatus.FAILED
            run.error_message = "Comparison job could not be queued"
            run.finished_at = datetime.now(UTC)
            item.status = ExperimentStatus.OPTIMIZATION_SUCCEEDED
            item.comparison_run_id = None
            item.updated_at = run.finished_at
            await self.repository.save_comparison_run(run)
            await self.repository.save(item)
            raise AppError(503, "COMPARISON_QUEUE_UNAVAILABLE", "Comparison could not be queued") from exc
        stored = await self.repository.get_comparison_run(run.id)
        return ComparisonRunResponse.model_validate(stored or run)

    async def get_comparison_run(self, run_id: str, owner_id: str) -> ComparisonRunResponse:
        run = await self.repository.get_comparison_run(run_id)
        if run is None:
            raise AppError(404, "COMPARISON_RUN_NOT_FOUND", "Comparison run was not found")
        await self._owned(run.experiment_id, owner_id)
        return ComparisonRunResponse.model_validate(run)

    async def get_comparison_artifact(self, run_id: str, artifact_name: str, owner_id: str) -> bytes:
        run = await self.repository.get_comparison_run(run_id)
        if run is None:
            raise AppError(404, "COMPARISON_RUN_NOT_FOUND", "Comparison run was not found")
        await self._owned(run.experiment_id, owner_id)
        object_name = run.artifact_objects.get(artifact_name)
        if object_name is None:
            raise AppError(404, "ARTIFACT_NOT_FOUND", "Artifact was not found in the run manifest")
        return await self.storage.read(object_name)

    async def execute_comparison(self, run_id: str) -> None:
        run = await self.repository.get_comparison_run(run_id)
        if run is None or run.status != ExperimentStatus.COMPARISON_QUEUED:
            return
        run.status = ExperimentStatus.COMPARING
        run.started_at = datetime.now(UTC)
        await self.repository.save_comparison_run(run)
        item = await self.repository.get(run.experiment_id)
        try:
            if item is None or self.executor is None:
                raise RuntimeError("Comparison sandbox is not configured")
            optimization = await self.repository.get_optimization_run(run.optimization_run_id)
            if optimization is None or not optimization.candidate_prompt:
                raise RuntimeError("The locked candidate prompt is unavailable")
            baseline = baseline_prompt()
            candidate = PromptBundle.from_candidate(optimization.candidate_prompt)
            if baseline.digest() != run.baseline_prompt_digest:
                raise RuntimeError("Baseline prompt digest changed before final evaluation")
            if candidate.digest() != run.candidate_prompt_digest:
                raise RuntimeError("Candidate prompt digest changed before final evaluation")
            project = await self.projects.require_owned(item.project_id, item.owner_id)
            functions = [await self._get_function(project.id, function_id) for function_id in run.test_target_ids]
            if any(function is None for function in functions):
                raise RuntimeError("A locked test function is no longer available")
            targets = [
                OptimizationTarget(
                    id=function.id,
                    symbol=function.qualified_name,
                    source=function.source,
                    split="test",
                    source_file=getattr(function, "file", ""),
                )
                for function in functions
                if function
            ]
            comparison = await compare_prompts(
                executor=self.executor,
                archive=await self._read_project_archive(project),
                source_directory=project.settings.runtime.source_directory,
                targets=targets,
                baseline=baseline,
                candidate=candidate,
                replicates=run.replicate_count,
            )
            report = {
                "protocol_version": 1,
                "baseline_prompt_digest": run.baseline_prompt_digest,
                "candidate_prompt_digest": run.candidate_prompt_digest,
                "test_target_ids": run.test_target_ids,
                "replicate_count": run.replicate_count,
                **comparison.as_dict(),
            }
            object_name = f"artifacts/{item.owner_id}/{item.project_id}/{item.id}/{run.id}/final_validation.json"
            await self.storage.write(
                object_name,
                json.dumps(report, ensure_ascii=False, indent=2).encode(),
                "application/json",
            )
            run.baseline_metrics = comparison.baseline
            run.candidate_metrics = comparison.candidate
            run.absolute_gain = comparison.absolute_gain
            run.relative_gain = comparison.relative_gain
            run.promotion_eligible = comparison.promotion_eligible
            run.decision_reason = comparison.decision_reason
            run.artifact_objects = {"final_validation.json": object_name}
            run.finished_at = datetime.now(UTC)
            if comparison.promotion_eligible:
                version = PromptVersionRecord(
                    id=new_id(),
                    experiment_id=item.id,
                    comparison_run_id=run.id,
                    parent_prompt_digest=run.baseline_prompt_digest,
                    prompt_digest=run.candidate_prompt_digest,
                    prompt=candidate.as_candidate(),
                    status=PromptVersionStatus.IN_REVIEW,
                    created_at=run.finished_at,
                )
                await self.repository.create_prompt_version(version)
                run.prompt_version_id = version.id
                run.status = ExperimentStatus.IN_REVIEW
                item.status = ExperimentStatus.IN_REVIEW
                item.prompt_version_id = version.id
            else:
                run.status = ExperimentStatus.COMPARISON_SUCCEEDED
                item.status = ExperimentStatus.OPTIMIZATION_SUCCEEDED
            item.updated_at = run.finished_at
        except Exception as exc:
            run.status = ExperimentStatus.FAILED
            run.error_message = str(exc)[-4000:]
            run.finished_at = datetime.now(UTC)
            if item:
                item.status = ExperimentStatus.OPTIMIZATION_SUCCEEDED
                item.updated_at = run.finished_at
        await self.repository.save_comparison_run(run)
        if item:
            await self.repository.save(item)

    async def get_prompt_version(self, version_id: str, owner_id: str) -> PromptVersionResponse:
        version = await self.repository.get_prompt_version(version_id)
        if version is None:
            raise AppError(404, "PROMPT_VERSION_NOT_FOUND", "Prompt version was not found")
        await self._owned(version.experiment_id, owner_id)
        return PromptVersionResponse.model_validate(version)

    async def list_prompt_versions(
        self,
        owner_id: str,
        status: PromptVersionStatus | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> PromptVersionListResponse:
        """List only versions belonging to the caller's experiments.

        Prompt versions intentionally inherit ownership from their experiment.  Looking up the
        owner's experiment records first keeps this safe for both the in-memory and Firestore
        repositories, without exposing a cross-tenant collection query.
        """
        experiments = await self.repository.list_for_owner(owner_id)
        versions = []
        for experiment in experiments:
            if not experiment.prompt_version_id:
                continue
            version = await self.repository.get_prompt_version(experiment.prompt_version_id)
            if version is not None and (status is None or version.status == status):
                versions.append(version)
        versions.sort(key=lambda item: item.created_at, reverse=True)
        total = len(versions)
        page = versions[offset : offset + limit]
        return PromptVersionListResponse(
            items=[PromptVersionResponse.model_validate(item) for item in page],
            total=total,
            offset=offset,
            limit=limit,
        )

    async def review_prompt_version(
        self, version_id: str, owner_id: str, decision: PromptVersionStatus, comment: str
    ) -> PromptVersionResponse:
        if decision not in {PromptVersionStatus.APPROVED, PromptVersionStatus.REJECTED}:
            raise ValueError("Review decision must be approved or rejected")
        version = await self.repository.get_prompt_version(version_id)
        if version is None:
            raise AppError(404, "PROMPT_VERSION_NOT_FOUND", "Prompt version was not found")
        item = await self._owned(version.experiment_id, owner_id)
        if version.status == decision:
            return PromptVersionResponse.model_validate(version)
        if version.status != PromptVersionStatus.IN_REVIEW:
            raise AppError(409, "PROMPT_VERSION_ALREADY_REVIEWED", "Prompt version already has a review decision")
        version = await self.repository.decide_prompt_version(
            version_id, decision, owner_id, comment, datetime.now(UTC)
        )
        if version is None:
            raise AppError(404, "PROMPT_VERSION_NOT_FOUND", "Prompt version was not found")
        if version.status != decision:
            raise AppError(409, "PROMPT_VERSION_ALREADY_REVIEWED", "Prompt version already has a review decision")
        item.status = (
            ExperimentStatus.APPROVED if decision == PromptVersionStatus.APPROVED else ExperimentStatus.REJECTED
        )
        item.updated_at = version.reviewed_at
        await self.repository.save(item)
        return PromptVersionResponse.model_validate(version)

    async def _owned(self, experiment_id, owner_id):
        item = await self.repository.get(experiment_id)
        if item is None or item.owner_id != owner_id:
            raise AppError(404, "EXPERIMENT_NOT_FOUND", "Experiment was not found")
        return item

    async def _list_functions(self, project_id: str):
        if self.samples and self.samples.contains(project_id):
            return self.samples.functions(project_id)
        return await self.functions.list_for_project(project_id)

    async def _get_function(self, project_id: str, function_id: str):
        if self.samples and self.samples.contains(project_id):
            return self.samples.function(project_id, function_id)
        return await self.functions.get(project_id, function_id)

    async def _read_project_archive(self, project) -> bytes:
        if self.samples and self.samples.contains(project.id):
            return self.samples.archive(project.id)
        return await self.storage.read(project.object_name)
