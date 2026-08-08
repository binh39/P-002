import io
import json
import re
import zipfile
from datetime import UTC, datetime

from src.core.errors import AppError
from src.infrastructure.storage import ObjectStorage
from src.modules.analysis.repository import FunctionRepository
from src.modules.projects.samples import SampleProjectCatalog
from src.modules.projects.service import ProjectService

from .dataset import select_targets, split_targets, validate_manual_splits
from .dispatcher import BaselineDispatcher, ComparisonDispatcher, OptimizationDispatcher
from .executor import DockerCoverUpExecutor
from .optimizer import OptimizationTarget
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
    ProjectSnapshot,
    PromptVersionListResponse,
    PromptVersionRecord,
    PromptVersionResponse,
    PromptVersionStatus,
    SamplingMethod,
    TargetReference,
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
        cloud_optimizer=None,
        samples: SampleProjectCatalog | None = None,
    ):
        self.repository, self.projects, self.functions = repository, projects, functions
        self.storage, self.executor = storage, executor
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
        projects = [await self.projects.require_owned(project_id, owner_id) for project_id in payload.project_ids]
        if any(project.status not in {"ready", "warning"} for project in projects):
            raise AppError(409, "ANALYSIS_NOT_READY", "Every project must finish analysis first")
        snapshots = []
        available: dict[str, TargetReference] = {}
        used_runner_names: set[str] = set()
        for index, project in enumerate(projects):
            runner_project = self._runner_project_name(project, index, used_runner_names)
            used_runner_names.add(runner_project)
            snapshots.append(
                ProjectSnapshot(
                    project_id=project.id,
                    name=project.name,
                    commit=project.commit,
                    source_directory=project.settings.runtime.source_directory,
                    test_directory=project.settings.tests.test_directory,
                    runner_project=runner_project,
                )
            )
            for function in await self._list_functions(project.id):
                if function.status != "Valid":
                    continue
                target = TargetReference(
                    project_id=project.id,
                    function_id=function.id,
                    project=runner_project,
                    source_file=function.file,
                    symbol=function.qualified_name,
                    statements=function.statements,
                    branches=function.branches,
                    loc=function.loc,
                )
                available[target.key] = target
        if len(available) < 3:
            raise AppError(422, "DATASET_TOO_SMALL", "At least three valid functions are required")
        try:
            if payload.sampling_method == SamplingMethod.MANUAL:
                selected, dataset_splits = validate_manual_splits(payload.manual_splits or {}, available)
            else:
                selected = select_targets(
                    available.values(), payload.sampling_method, payload.random_seed, payload.max_targets
                )
                dataset_splits = split_targets(selected, payload.split_percentages, payload.random_seed)
        except ValueError as exc:
            raise AppError(422, "INVALID_EXPERIMENT_DATASET", str(exc)) from exc
        if not all(dataset_splits[name] for name in ("train", "validation", "test")):
            raise AppError(422, "DATASET_SPLIT_EMPTY", "Train, validation, and test must all be non-empty")
        now = datetime.now(UTC)
        item = ExperimentRecord(
            id=new_id(),
            owner_id=owner_id,
            project_id=projects[0].id,
            project_ids=[project.id for project in projects],
            project_snapshots=snapshots,
            name=payload.name,
            target_function_ids=[target.key for target in selected],
            targets=selected,
            sampling_method=payload.sampling_method,
            max_targets=payload.max_targets,
            dataset_splits=dataset_splits,
            split_percentages=payload.split_percentages,
            split_seed=payload.random_seed,
            settings=payload.settings,
            optimization_eligible=True,
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

    async def delete(self, experiment_id: str, owner_id: str) -> None:
        item = await self._owned(experiment_id, owner_id)
        active = {
            ExperimentStatus.BASELINE_QUEUED,
            ExperimentStatus.BASELINE_RUNNING,
            ExperimentStatus.OPTIMIZATION_QUEUED,
            ExperimentStatus.OPTIMIZING,
            ExperimentStatus.CANDIDATE_EVALUATING,
            ExperimentStatus.COMPARISON_QUEUED,
            ExperimentStatus.COMPARING,
        }
        if item.status in active:
            raise AppError(409, "EXPERIMENT_ACTIVE", "A running experiment cannot be deleted")
        await self.repository.delete(item.id)

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
            prompt = baseline_prompt()
            targets_by_project: dict[str, list[TargetReference]] = {}
            for target in item.targets:
                targets_by_project.setdefault(target.project_id, []).append(target)
            executions = []
            for snapshot in item.project_snapshots:
                project_targets = targets_by_project.get(snapshot.project_id, [])
                if not project_targets:
                    continue
                project = await self.projects.require_owned(snapshot.project_id, item.owner_id)
                execution = await self.executor.execute(
                    await self._read_project_archive(project),
                    snapshot.source_directory,
                    [target.symbol for target in project_targets],
                    prompt,
                    item.settings,
                )
                executions.append((snapshot, project_targets, execution))
            if not executions:
                raise RuntimeError("No baseline targets are available")
            artifact_objects: dict[str, str] = {}
            target_metrics: dict[str, dict] = {}
            content_types = {
                "coverage_after.json": "application/json",
                "prompt.json": "application/json",
                "attempt_trace.jsonl": "application/x-ndjson",
                "generated_tests.zip": "application/zip",
                "target_coverage.json": "application/json",
            }
            for snapshot, project_targets, execution in executions:
                for target in project_targets:
                    target_metrics[target.key] = execution.target_metrics.get(target.symbol, {})
                for name, content in execution.artifacts.items():
                    artifact_name = f"{snapshot.runner_project}__{name}"
                    object_name = f"artifacts/{item.owner_id}/{item.id}/{run.id}/{artifact_name}"
                    await self.storage.write(object_name, content, content_types.get(name, "text/plain"))
                    artifact_objects[artifact_name] = object_name
            statement, branch, score = self._aggregate_target_metrics(target_metrics)
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
                score,
                statement,
                branch,
                prompt.digest(),
                artifact_objects,
                target_metrics,
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
            if item is None or self.cloud_optimizer is None:
                raise RuntimeError("Cloud GEPA optimizer is not configured")
            baseline_run = await self.repository.get_run(item.baseline_run_id or "")
            parent = baseline_prompt()
            if baseline_run is None or baseline_run.prompt_digest != parent.digest():
                raise RuntimeError("Baseline prompt version is unavailable or has changed")
            references = {target.key: target for target in item.targets}
            if set(item.target_function_ids) != set(references):
                raise RuntimeError("The immutable target snapshot is incomplete")
            targets = {
                split: [
                    OptimizationTarget(
                        id=target_key,
                        project=references[target_key].project,
                        symbol=references[target_key].symbol,
                        source=(await self._require_target_source(references[target_key], item.owner_id)),
                        split=split,
                        source_file=references[target_key].source_file,
                    )
                    for target_key in item.dataset_splits[split]
                ]
                for split in ("train", "validation")
            }
            holdout = [
                OptimizationTarget(
                    id=target_key,
                    project=references[target_key].project,
                    symbol=references[target_key].symbol,
                    source=await self._require_target_source(references[target_key], item.owner_id),
                    split="test",
                    source_file=references[target_key].source_file,
                )
                for target_key in item.dataset_splits["test"]
            ]
            archive, project_layouts = await self._build_cloud_archive(item)
            result = await self.cloud_optimizer.optimize(
                archive=archive,
                project_layouts=project_layouts,
                baseline=parent,
                train=targets["train"],
                validation=targets["validation"],
                holdout=holdout,
                settings=item.settings,
            )
            artifact_payloads = {
                "candidate_prompt.json": (result.candidate.as_json().encode(), "application/json"),
                "gepa_result.json": (
                    json.dumps(result.gepa_result, ensure_ascii=False, indent=2, default=str).encode(),
                    "application/json",
                ),
            }
            artifact_objects = {}
            for name, (content, content_type) in artifact_payloads.items():
                object_name = f"artifacts/{item.owner_id}/{item.id}/{run.id}/{name}"
                await self.storage.write(object_name, content, content_type)
                artifact_objects[name] = object_name
            run.status = ExperimentStatus.OPTIMIZATION_SUCCEEDED
            run.candidate_prompt = result.candidate.as_candidate()
            run.candidate_prompt_digest = result.candidate.digest()
            run.baseline_validation_score = result.baseline_score
            run.candidate_validation_score = result.score
            run.candidate_count = result.candidate_count
            run.metric_calls = result.metric_calls
            run.final_validation = result.gepa_result.get("final_validation", {})
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
            replicate_count=item.settings.evaluation_replicates,
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
            if item is None:
                raise RuntimeError("Experiment is unavailable")
            optimization = await self.repository.get_optimization_run(run.optimization_run_id)
            if optimization is None or not optimization.candidate_prompt:
                raise RuntimeError("The locked candidate prompt is unavailable")
            candidate = PromptBundle.from_candidate(optimization.candidate_prompt)
            if candidate.digest() != run.candidate_prompt_digest:
                raise RuntimeError("Candidate prompt digest changed before final evaluation")
            report = optimization.final_validation
            if not report:
                raise RuntimeError("Cloud GEPA final validation is unavailable")
            baseline_metrics = self._comparison_metrics(report.get("baseline_aggregate_coverage"))
            candidate_metrics = self._comparison_metrics(report.get("optimized_aggregate_coverage"))
            absolute_gain = report.get("absolute_gain")
            promoted = bool(report.get("promoted"))
            baseline_score = baseline_metrics.get("score")
            relative_gain = (
                float(absolute_gain) / float(baseline_score) if absolute_gain is not None and baseline_score else None
            )
            reason = (
                "Candidate strictly improved paired coverage on the locked holdout"
                if promoted
                else report.get("skip_reason") or "Candidate did not strictly improve the locked holdout"
            )
            object_name = f"artifacts/{item.owner_id}/{item.id}/{run.id}/final_validation.json"
            await self.storage.write(
                object_name,
                json.dumps(report, ensure_ascii=False, indent=2).encode(),
                "application/json",
            )
            run.baseline_metrics = baseline_metrics
            run.candidate_metrics = candidate_metrics
            run.absolute_gain = absolute_gain
            run.relative_gain = relative_gain
            run.promotion_eligible = promoted
            run.decision_reason = reason
            run.artifact_objects = {"final_validation.json": object_name}
            run.finished_at = datetime.now(UTC)
            if promoted:
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

    @staticmethod
    def _runner_project_name(project, index: int, used: set[str]) -> str:
        base = re.sub(r"[^A-Za-z0-9_.-]+", "-", project.name.lower()).strip(".-") or f"project-{index + 1}"
        candidate = base
        suffix = 2
        while candidate in used:
            candidate = f"{base}-{suffix}"
            suffix += 1
        return candidate

    async def _require_target_source(self, target: TargetReference, owner_id: str) -> str:
        await self.projects.require_owned(target.project_id, owner_id)
        function = await self._get_function(target.project_id, target.function_id)
        if function is None:
            raise RuntimeError(f"Target is no longer available: {target.key}")
        return function.source

    async def _build_cloud_archive(self, item: ExperimentRecord) -> tuple[bytes, dict[str, dict[str, str]]]:
        output = io.BytesIO()
        layouts: dict[str, dict[str, str]] = {}
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as destination:
            for snapshot in item.project_snapshots:
                project = await self.projects.require_owned(snapshot.project_id, item.owner_id)
                archive = await self._read_project_archive(project)
                with zipfile.ZipFile(io.BytesIO(archive)) as source:
                    for entry in source.infolist():
                        if entry.is_dir():
                            continue
                        normalized = entry.filename.replace("\\", "/").lstrip("/")
                        if ".." in normalized.split("/"):
                            raise RuntimeError("Project archive contains an unsafe path")
                        destination.writestr(f"projects/{snapshot.runner_project}/{normalized}", source.read(entry))
                root = f"projects/{snapshot.runner_project}"
                layouts[snapshot.runner_project] = {
                    "package_dir": f"{root}/{snapshot.source_directory.strip('/')}",
                    "tests_dir": f"{root}/{snapshot.test_directory.strip('/')}",
                }
        return output.getvalue(), layouts

    @staticmethod
    def _aggregate_target_metrics(metrics: dict[str, dict]) -> tuple[float | None, float | None, float]:
        valid = [metric for metric in metrics.values() if metric.get("valid")]
        covered_statements = sum(int(metric.get("covered_statements", 0)) for metric in valid)
        statements = sum(int(metric.get("num_statements", 0)) for metric in valid)
        covered_branches = sum(int(metric.get("covered_branches", 0)) for metric in valid)
        branches = sum(int(metric.get("num_branches", 0)) for metric in valid)
        statement = covered_statements / statements if statements else None
        branch = covered_branches / branches if branches else None
        score = statement if branch is None else 0.4 * (statement or 0.0) + 0.6 * branch
        return statement, branch, score or 0.0

    @staticmethod
    def _comparison_metrics(coverage: dict | None) -> dict:
        coverage = coverage or {}
        return {
            "score": coverage.get("score"),
            "statement_coverage": coverage.get("statement_coverage"),
            "branch_coverage": coverage.get("branch_coverage"),
            "pass_rate": coverage.get("pass_rate"),
            "sample_count": coverage.get("sample_count"),
            "timeout_count": coverage.get("timeout_count"),
            "flaky_targets": coverage.get("flaky_targets", []),
        }
