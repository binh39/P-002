from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta

from google.api_core import exceptions as google_api_exceptions

from backend.core.errors import AppError
from backend.infrastructure.storage import ObjectStorage
from backend.modules.analysis.repository import FunctionRepository
from backend.modules.analysis.schemas import is_valid_optimization_function, normalize_optimization_source_file
from backend.modules.projects.samples import SampleProjectCatalog
from backend.modules.projects.schemas import MINIMUM_RUNTIME_PROTOCOL_VERSION, RuntimeStatus
from backend.modules.projects.service import ProjectService

from .cloud_optimizer import OptimizationPausedError
from .dataset import select_targets, split_targets, validate_manual_splits
from .dispatcher import ComparisonDispatcher, OptimizationDispatcher, TestGenerationDispatcher
from .evolution import merge_evolution_history
from .optimizer import OptimizationTarget
from .prompts import PromptBundle, baseline_prompt
from .repository import ExperimentRepository
from .schemas import (
    ComparisonRunRecord,
    ComparisonRunResponse,
    CreateExperimentRequest,
    CreateTestGenerationRequest,
    EvolutionResponse,
    ExperimentListResponse,
    ExperimentRecord,
    ExperimentResponse,
    ExperimentStatus,
    OptimizationRunRecord,
    OptimizationRunResponse,
    ProjectSnapshot,
    PromptCoverageMetrics,
    PromptRegistryEntryResponse,
    PromptRegistryListResponse,
    PromptRole,
    PromptSnapshotOrigin,
    PromptSnapshotRecord,
    PromptSnapshotResponse,
    PromptVersionListResponse,
    PromptVersionRecord,
    PromptVersionResponse,
    PromptVersionStatus,
    SamplingMethod,
    TargetReference,
    TestGenerationMetrics,
    TestGenerationRunListResponse,
    TestGenerationRunRecord,
    TestGenerationRunResponse,
    TestGenerationScope,
    TestGenerationStatus,
    new_id,
)

STANDARD_MAX_METRIC_CALLS = 2200
STANDARD_MAX_EXPERIMENT_TARGETS = 20
MAX_TEST_GENERATION_MANIFEST_BYTES = 1_000_000
MAX_TEST_GENERATION_ARTIFACT_FILES = 1_000

ACTIVE_EXPERIMENT_STATUSES = frozenset(
    {
        ExperimentStatus.BASELINE_QUEUED,
        ExperimentStatus.BASELINE_RUNNING,
        ExperimentStatus.OPTIMIZATION_QUEUED,
        ExperimentStatus.OPTIMIZING,
        ExperimentStatus.CANDIDATE_EVALUATING,
        ExperimentStatus.COMPARISON_QUEUED,
        ExperimentStatus.COMPARING,
    }
)

_TRANSIENT_CLOUD_STATUS_CODES = {408, 429, 500, 502, 503, 504}


def _is_transient_cloud_error(error: BaseException) -> bool:
    """Return whether a cloud transport failure is safe to retry.

    Cloud clients commonly wrap gRPC connection resets in ``GoogleAPICallError``
    (for example ``503 Stream removed``). Those failures say nothing about the
    underlying GEPA execution and must not turn a running optimization into a
    terminal failure.
    """
    pending: list[BaseException] = [error]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, (ConnectionError, TimeoutError)):
            return True
        if isinstance(current, google_api_exceptions.GoogleAPICallError):
            status_code = getattr(current, "code", None)
            if status_code in _TRANSIENT_CLOUD_STATUS_CODES:
                return True
        for nested in (current.__cause__, current.__context__):
            if isinstance(nested, BaseException):
                pending.append(nested)
    return False


_FINAL_VALIDATION_SCALAR_FIELDS = (
    "mean_score",
    "baseline_mean_score",
    "optimized_mean_score",
    "absolute_gain",
    "promoted",
    "final_evaluation_skipped",
    "skip_reason",
    "final_split",
    "used_locked_holdout",
    "evaluation_replicates",
)
_FINAL_VALIDATION_METRIC_FIELDS = (
    "score",
    "statement_coverage",
    "branch_coverage",
    "pass_rate",
    "latency_seconds",
    "sample_count",
    "timeout_count",
    "flaky_targets",
)


def _compact_final_validation(report: dict) -> dict:
    """Return the Firestore-safe subset used by the API and comparison flow.

    The complete report remains in the GCS optimization artifacts. Per-target
    traces include arrays of branch-coordinate arrays, which Firestore rejects
    as nested array values and which are not needed to render the result.
    """
    compact = {field: report[field] for field in _FINAL_VALIDATION_SCALAR_FIELDS if field in report}
    for aggregate_field in ("baseline_aggregate_coverage", "optimized_aggregate_coverage"):
        aggregate = report.get(aggregate_field)
        if isinstance(aggregate, dict):
            compact[aggregate_field] = {
                field: aggregate[field] for field in _FINAL_VALIDATION_METRIC_FIELDS if field in aggregate
            }
    return compact


def _redact_artifact_value(value):
    """Remove credential-shaped fields before returning a JSON artifact to a browser."""
    if isinstance(value, list):
        return [_redact_artifact_value(item) for item in value]
    if not isinstance(value, dict):
        return value
    redacted = {}
    for key, item in value.items():
        normalized = str(key).lower()
        if any(marker in normalized for marker in ("api_key", "token", "secret", "credential", "authorization")):
            redacted[key] = "[redacted]"
        else:
            redacted[key] = _redact_artifact_value(item)
    return redacted


def _validated_final_test_artifact_objects(prefix: str, artifacts: dict) -> dict[str, str]:
    """Map the runner's constrained artifact index to owner-scoped object aliases."""
    objects = {
        "manifest": f"{prefix}/{artifacts.get('manifest', 'test_generation_result.json')}",
        "suite_zip": f"{prefix}/{artifacts.get('suite_zip', 'generated_tests.zip')}",
    }
    files = artifacts.get("files")
    if not isinstance(files, list):
        return objects
    for entry in files[:MAX_TEST_GENERATION_ARTIFACT_FILES]:
        if not isinstance(entry, dict):
            continue
        artifact_id, kind, relative_path = entry.get("id"), entry.get("kind"), entry.get("path")
        if not all(isinstance(value, str) for value in (artifact_id, kind, relative_path)):
            continue
        if not re.fullmatch(r"[a-z0-9-]{1,80}", artifact_id):
            continue
        if kind == "generated_test":
            expected_prefix, expected_suffix = "generated_tests/", ".py"
        elif kind == "source":
            expected_prefix, expected_suffix = "source/", ".py"
        elif kind == "coverage":
            expected_prefix, expected_suffix = "coverage/", ".json"
        else:
            continue
        normalized_path = relative_path.replace("\\", "/")
        path_parts = normalized_path.split("/")
        if (
            not normalized_path.startswith(expected_prefix)
            or not normalized_path.endswith(expected_suffix)
            or ".." in path_parts
            or (kind == "source" and len(path_parts) < 3)
        ):
            continue
        objects[f"file-{artifact_id}"] = f"{prefix}/{normalized_path}"
    return objects


class ExperimentService:
    def __init__(
        self,
        repository: ExperimentRepository,
        projects: ProjectService,
        functions: FunctionRepository,
        storage: ObjectStorage,
        cloud_optimizer=None,
        cloud_test_generator=None,
        samples: SampleProjectCatalog | None = None,
        admin_vertexai_project: str = "",
        provider_credentials=None,
        runtime_bundle_protocol_version: int = MINIMUM_RUNTIME_PROTOCOL_VERSION,
    ):
        self.repository, self.projects, self.functions = repository, projects, functions
        self.storage = storage
        self.cloud_optimizer = cloud_optimizer
        self.cloud_test_generator = cloud_test_generator
        self.samples = samples
        self.admin_vertexai_project = admin_vertexai_project.strip()
        self.provider_credentials = provider_credentials
        self.runtime_bundle_protocol_version = runtime_bundle_protocol_version
        self.optimization_dispatcher: OptimizationDispatcher | None = None
        self.comparison_dispatcher: ComparisonDispatcher | None = None
        self.test_generation_dispatcher: TestGenerationDispatcher | None = None

    def set_optimization_dispatcher(self, dispatcher: OptimizationDispatcher) -> None:
        self.optimization_dispatcher = dispatcher

    def set_comparison_dispatcher(self, dispatcher: ComparisonDispatcher) -> None:
        self.comparison_dispatcher = dispatcher

    def set_test_generation_dispatcher(self, dispatcher: TestGenerationDispatcher) -> None:
        self.test_generation_dispatcher = dispatcher

    async def _enforce_standard_account_concurrency(
        self,
        owner_id: str,
        *,
        full_access: bool,
        exclude_experiment_id: str | None = None,
    ) -> None:
        if full_access:
            return
        active = next(
            (
                item
                for item in await self.repository.list_for_owner(owner_id)
                if item.id != exclude_experiment_id and item.status in ACTIVE_EXPERIMENT_STATUSES
            ),
            None,
        )
        if active is not None:
            raise AppError(
                409,
                "ACTIVE_EXPERIMENT_LIMIT",
                "Standard accounts can run only one experiment at a time",
            )

    @staticmethod
    def _baseline_for(item: ExperimentRecord) -> PromptBundle:
        candidate = item.baseline_prompt
        prompt = PromptBundle.from_candidate(candidate) if candidate is not None else baseline_prompt()
        prompt.validate()
        return prompt

    @staticmethod
    def _stable_digest(payload: object) -> str:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()[:32]

    @classmethod
    def _source_snapshot_digest(cls, item: ExperimentRecord) -> str:
        projects = [snapshot.model_dump(mode="json") for snapshot in item.project_snapshots]
        return cls._stable_digest({"project_ids": item.project_ids, "projects": projects})

    @classmethod
    def _dataset_digest(cls, item: ExperimentRecord) -> str:
        targets = [target.model_dump(mode="json") for target in item.targets]
        return cls._stable_digest(
            {
                "targets": targets,
                "splits": item.dataset_splits,
                "seed": item.split_seed,
                "sampling_method": item.sampling_method.value,
            }
        )

    @staticmethod
    def _coverage_metrics(raw: dict | None) -> PromptCoverageMetrics:
        raw = raw or {}
        return PromptCoverageMetrics(
            score=raw.get("score"),
            statement_coverage=raw.get("statement_coverage"),
            branch_coverage=raw.get("branch_coverage"),
            pass_rate=raw.get("pass_rate"),
        )

    @staticmethod
    def _runner_protocol_version(item: ExperimentRecord) -> int:
        return max((snapshot.runtime_protocol_version for snapshot in item.project_snapshots), default=1)

    def _new_prompt_snapshot(
        self,
        item: ExperimentRecord,
        *,
        role: PromptRole,
        origin: PromptSnapshotOrigin,
        prompt: PromptBundle,
        metrics: PromptCoverageMetrics | None = None,
        created_at: datetime | None = None,
    ) -> PromptSnapshotRecord:
        return PromptSnapshotRecord(
            id=f"{item.id}:{role.value}",
            owner_id=item.owner_id,
            experiment_id=item.id,
            project_ids=list(item.project_ids),
            role=role,
            origin=origin,
            prompt_digest=prompt.digest(),
            prompt=prompt.as_candidate(),
            source_snapshot_digest=self._source_snapshot_digest(item),
            dataset_digest=self._dataset_digest(item),
            split_seed=item.split_seed,
            runner_protocol_version=self._runner_protocol_version(item),
            coverup_model=item.settings.coverup_model,
            optimize_model=item.settings.optimize_model,
            metrics=metrics or PromptCoverageMetrics(),
            created_at=created_at or datetime.now(UTC),
        )

    async def _ensure_baseline_prompt_snapshot(self, item: ExperimentRecord) -> PromptSnapshotRecord:
        existing = await self.repository.get_prompt_snapshot(item.id, PromptRole.BASELINE)
        if existing is not None:
            return existing
        snapshot = self._new_prompt_snapshot(
            item,
            role=PromptRole.BASELINE,
            origin=PromptSnapshotOrigin.INITIAL_BASELINE,
            prompt=self._baseline_for(item),
            created_at=item.created_at,
        )
        await self.repository.create_prompt_snapshot(snapshot)
        return snapshot

    async def _ensure_optimized_prompt_snapshot(
        self, item: ExperimentRecord, comparison: ComparisonRunRecord | None = None
    ) -> PromptSnapshotRecord | None:
        existing = await self.repository.get_prompt_snapshot(item.id, PromptRole.OPTIMIZED)
        if existing is not None:
            return existing
        comparison = comparison or (
            await self.repository.get_comparison_run(item.comparison_run_id) if item.comparison_run_id else None
        )
        if comparison is None or comparison.status not in {
            ExperimentStatus.COMPARISON_SUCCEEDED,
            ExperimentStatus.IN_REVIEW,
        }:
            return None

        prompt = self._baseline_for(item)
        origin = PromptSnapshotOrigin.BASELINE_RETAINED
        metrics = self._coverage_metrics(comparison.baseline_metrics)
        if comparison.promotion_eligible:
            optimization = await self.repository.get_optimization_run(comparison.optimization_run_id)
            if optimization is None or not optimization.candidate_prompt:
                return None
            candidate = PromptBundle.from_candidate(optimization.candidate_prompt)
            if candidate.digest() != comparison.candidate_prompt_digest:
                return None
            prompt = candidate
            origin = PromptSnapshotOrigin.OPTIMIZED_CANDIDATE
            metrics = self._coverage_metrics(comparison.candidate_metrics)
        snapshot = self._new_prompt_snapshot(
            item,
            role=PromptRole.OPTIMIZED,
            origin=origin,
            prompt=prompt,
            metrics=metrics,
            created_at=comparison.finished_at or comparison.created_at,
        )
        await self.repository.create_prompt_snapshot(snapshot)
        return snapshot

    async def create(
        self,
        owner_id: str,
        payload: CreateExperimentRequest,
        *,
        full_access: bool = False,
    ) -> ExperimentResponse:
        if not full_access and payload.settings.max_metric_calls > STANDARD_MAX_METRIC_CALLS:
            raise AppError(
                403,
                "METRIC_BUDGET_LIMIT",
                f"Metric-call budget is limited to {STANDARD_MAX_METRIC_CALLS}",
            )
        await self._enforce_standard_account_concurrency(owner_id, full_access=full_access)
        try:
            parent = (
                PromptBundle(
                    initial=payload.baseline_prompt.initial,
                    error=payload.baseline_prompt.error,
                    missing_coverage=(payload.baseline_prompt.missing_coverage or baseline_prompt().missing_coverage),
                )
                if payload.baseline_prompt is not None
                else baseline_prompt()
            )
            parent.validate()
        except (KeyError, ValueError) as exc:
            raise AppError(422, "INVALID_BASELINE_PROMPT", str(exc)) from exc
        projects = [await self.projects.require_owned(project_id, owner_id) for project_id in payload.project_ids]
        if self.projects.runtime:
            projects = [
                project if self.projects.is_sample(project.id) else await self.projects.runtime.refresh(project)
                for project in projects
            ]
        if any(project.status not in {"ready", "warning"} for project in projects):
            raise AppError(409, "ANALYSIS_NOT_READY", "Every project must finish analysis first")
        uploaded = [project for project in projects if not self.projects.is_sample(project.id)]
        if any(project.runtime_status != RuntimeStatus.READY for project in uploaded):
            raise AppError(409, "RUNTIME_NOT_READY", "Every uploaded project must pass runtime preparation")
        outdated_runtime = [
            project
            for project in uploaded
            if project.runtime_report is None
            or project.runtime_report.protocol_version < MINIMUM_RUNTIME_PROTOCOL_VERSION
            or not project.runtime_bundle_object
            or not project.runtime_digest
            or not project.runtime_image
            or not project.runtime_worker_job
            or not project.source_archive_sha256
            or not project.runtime_bundle_sha256
            or project.runtime_report.python_version != project.settings.runtime.python_version
        ]
        if outdated_runtime:
            raise AppError(
                409,
                "RUNTIME_REBUILD_REQUIRED",
                "One or more uploaded projects use an outdated runtime; rebuild the runtime before creating an experiment",
            )
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
                    archive_object=(
                        None
                        if self.projects.is_sample(project.id)
                        else (project.runtime_source_archive_object or project.object_name)
                    ),
                    runtime_artifact_prefix=project.runtime_artifact_prefix,
                    runtime_environment_id=project.runtime_environment_id,
                    runtime_bundle_object=project.runtime_bundle_object,
                    runtime_protocol_version=(project.runtime_report.protocol_version if project.runtime_report else 1),
                    runtime_digest=project.runtime_digest or project.runtime_dependency_fingerprint,
                    runtime_image=project.runtime_image or project.settings.runtime.runtime_image,
                    runtime_worker_job=project.runtime_worker_job,
                    runtime_execution_mode=(
                        project.runtime_report.execution_mode if project.runtime_report else None
                    ),
                    source_archive_sha256=project.source_archive_sha256,
                    runtime_bundle_sha256=project.runtime_bundle_sha256,
                    python_version=project.settings.runtime.python_version,
                )
            )
            for function in await self._list_functions(project.id):
                if not is_valid_optimization_function(function):
                    continue
                runner_source_file = self._runner_source_file(project, function.file)
                if runner_source_file is None:
                    continue
                target = TargetReference(
                    project_id=project.id,
                    function_id=function.id,
                    project=runner_project,
                    source_file=runner_source_file,
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
        if not full_access and len(selected) > STANDARD_MAX_EXPERIMENT_TARGETS:
            raise AppError(
                403,
                "EXPERIMENT_TARGET_LIMIT",
                f"Standard accounts can select at most {STANDARD_MAX_EXPERIMENT_TARGETS} functions",
            )
        if not all(dataset_splits[name] for name in ("train", "validation", "test")):
            raise AppError(422, "DATASET_SPLIT_EMPTY", "Train, validation, and test must all be non-empty")
        validation_size = len(dataset_splits["validation"])
        if payload.settings.max_metric_calls <= validation_size:
            raise AppError(
                422,
                "METRIC_BUDGET_TOO_SMALL",
                (
                    f"Max metric calls must be greater than the {validation_size} validation targets "
                    "so GEPA can finish iteration 0 and start at least one proposal iteration"
                ),
            )
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
            baseline_prompt=parent.as_candidate(),
            optimization_eligible=all(
                self.projects.is_sample(project.id) or project.runtime_status == RuntimeStatus.READY
                for project in projects
            ),
            status=ExperimentStatus.DRAFT,
            created_at=now,
            updated_at=now,
        )
        await self.repository.create(item)
        await self._ensure_baseline_prompt_snapshot(item)
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
        if item.status in ACTIVE_EXPERIMENT_STATUSES:
            raise AppError(409, "EXPERIMENT_ACTIVE", "A running experiment cannot be deleted")
        await self.repository.delete(item.id)

    async def request_optimization(
        self,
        experiment_id: str,
        owner_id: str,
        *,
        full_access: bool = False,
    ) -> OptimizationRunResponse:
        item = await self._owned(experiment_id, owner_id)
        await self._enforce_standard_account_concurrency(
            owner_id,
            full_access=full_access,
            exclude_experiment_id=item.id,
        )
        previous_status = item.status
        previous_run_id = item.optimization_run_id
        retryable_statuses = {
            ExperimentStatus.FAILED,
            ExperimentStatus.TIMED_OUT,
            ExperimentStatus.CANCELLED,
        }
        previous_run = await self.repository.get_optimization_run(previous_run_id) if previous_run_id else None
        retrying_failed_optimization = (
            previous_status in retryable_statuses
            and previous_run is not None
            and previous_run.status in retryable_statuses
        )
        if previous_status != ExperimentStatus.DRAFT and not retrying_failed_optimization:
            raise AppError(409, "OPTIMIZATION_ALREADY_REQUESTED", "Optimization has already been requested")
        if not item.optimization_eligible:
            raise AppError(
                409,
                "OPTIMIZATION_DATASET_TOO_SMALL",
                "Optimization requires non-empty train, validation, and locked test splits",
            )
        if any(
            snapshot.archive_object and snapshot.runtime_protocol_version != self.runtime_bundle_protocol_version
            for snapshot in item.project_snapshots
        ):
            raise AppError(
                409,
                "RUNTIME_BUNDLE_STALE",
                "Runtime dependencies changed; prepare the uploaded project runtime again before running this experiment",
            )
        if self.optimization_dispatcher is None:
            raise RuntimeError("Optimization dispatcher is not configured")
        parent = self._baseline_for(item)
        provider_secret_refs = {}
        if self.provider_credentials is not None:
            provider_secret_refs = await self.provider_credentials.resolve_for_models(
                owner_id,
                [item.settings.coverup_model, item.settings.optimize_model],
            )

        now = datetime.now(UTC)
        run = OptimizationRunRecord(
            id=new_id(),
            experiment_id=item.id,
            status=ExperimentStatus.OPTIMIZATION_QUEUED,
            parent_prompt_digest=parent.digest(),
            vertexai_project=self.admin_vertexai_project if full_access else None,
            provider_secret_refs={
                environment: {"secret": reference.secret, "version": reference.version}
                for environment, reference in provider_secret_refs.items()
            },
            max_concurrency=item.settings.max_concurrency,
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
            item.status = previous_status
            item.optimization_run_id = previous_run_id
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

    async def cancel_optimization(self, run_id: str, owner_id: str) -> OptimizationRunResponse:
        run = await self.repository.get_optimization_run(run_id)
        if run is None:
            raise AppError(404, "OPTIMIZATION_RUN_NOT_FOUND", "Optimization run was not found")
        item = await self._owned(run.experiment_id, owner_id)
        if run.status == ExperimentStatus.CANCELLED:
            return OptimizationRunResponse.model_validate(run)
        active_statuses = {
            ExperimentStatus.OPTIMIZATION_QUEUED,
            ExperimentStatus.OPTIMIZING,
            ExperimentStatus.CANDIDATE_EVALUATING,
        }
        if run.status not in active_statuses:
            raise AppError(409, "OPTIMIZATION_NOT_ACTIVE", "Only an active optimization can be cancelled")
        if run.cloud_artifact_prefix:
            if self.cloud_optimizer is None or not hasattr(self.cloud_optimizer, "cancel"):
                raise AppError(503, "CANCELLATION_UNAVAILABLE", "Cloud Run cancellation is not configured")
            try:
                await self.cloud_optimizer.cancel(
                    run.cloud_artifact_prefix,
                    started_at=run.started_at,
                )
            except Exception as exc:
                detail = str(exc).strip() or type(exc).__name__
                raise AppError(503, "CANCELLATION_FAILED", detail[:500]) from exc
            if hasattr(self.cloud_optimizer, "evolution"):
                try:
                    evolution = await self.cloud_optimizer.evolution(
                        run.cloud_artifact_prefix,
                        started_at=run.started_at,
                    )
                    if evolution.available and evolution.iterations:
                        object_name = self._optimization_artifact_name(item, run, "evolution.json")
                        await self.storage.write(
                            object_name,
                            evolution.model_dump_json(indent=2).encode(),
                            "application/json",
                        )
                        run.artifact_objects["evolution.json"] = object_name
                except Exception:
                    # Cancellation must succeed even if the optional history snapshot fails.
                    pass
        now = datetime.now(UTC)
        run.status = ExperimentStatus.CANCELLED
        run.finished_at = now
        item.status = ExperimentStatus.CANCELLED
        item.updated_at = now
        await self.repository.save_optimization_run(run)
        await self.repository.save(item)
        return OptimizationRunResponse.model_validate(run)

    async def resume_optimization(
        self,
        run_id: str,
        owner_id: str,
        *,
        max_concurrency: int | None = None,
        full_access: bool = False,
    ) -> OptimizationRunResponse:
        """Queue a new Cloud Run execution from a cooperatively paused checkpoint."""
        run = await self.repository.get_optimization_run(run_id)
        if run is None:
            raise AppError(404, "OPTIMIZATION_RUN_NOT_FOUND", "Optimization run was not found")
        item = await self._owned(run.experiment_id, owner_id)
        await self._enforce_standard_account_concurrency(
            owner_id,
            full_access=full_access,
            exclude_experiment_id=item.id,
        )
        if run.status != ExperimentStatus.PAUSED:
            raise AppError(409, "OPTIMIZATION_NOT_PAUSED", "Only a paused optimization can be resumed")
        if not run.cloud_artifact_prefix:
            raise AppError(409, "OPTIMIZATION_CHECKPOINT_MISSING", "The paused checkpoint is unavailable")
        if self.optimization_dispatcher is None:
            raise AppError(503, "OPTIMIZATION_QUEUE_UNAVAILABLE", "Optimization dispatcher is not configured")
        if max_concurrency is not None and not 1 <= max_concurrency <= 32:
            raise AppError(422, "INVALID_MAX_CONCURRENCY", "Maximum concurrency must be between 1 and 32")

        checkpoint_prefix = run.cloud_artifact_prefix
        run.max_concurrency = max_concurrency or run.max_concurrency or item.settings.max_concurrency
        run.resume_artifact_prefix = checkpoint_prefix
        run.cloud_artifact_prefix = None
        run.cloud_deadline_at = None
        run.status = ExperimentStatus.OPTIMIZATION_QUEUED
        run.pause_reason = None
        run.error_message = None
        run.finished_at = None
        run.resume_count += 1
        item.status = ExperimentStatus.OPTIMIZATION_QUEUED
        item.updated_at = datetime.now(UTC)
        await self.repository.save_optimization_run(run)
        await self.repository.save(item)
        try:
            await self.optimization_dispatcher.dispatch(run.id)
        except Exception as exc:
            run.status = ExperimentStatus.PAUSED
            run.cloud_artifact_prefix = checkpoint_prefix
            run.pause_reason = "Could not queue the resume execution"
            item.status = ExperimentStatus.PAUSED
            item.updated_at = datetime.now(UTC)
            await self.repository.save_optimization_run(run)
            await self.repository.save(item)
            raise AppError(503, "OPTIMIZATION_QUEUE_UNAVAILABLE", "Optimization could not be resumed") from exc
        return OptimizationRunResponse.model_validate(run)

    async def _load_evolution_snapshot(
        self,
        run: OptimizationRunRecord,
    ) -> EvolutionResponse | None:
        snapshot_object = run.artifact_objects.get("evolution.json")
        if not snapshot_object:
            return None
        try:
            return EvolutionResponse.model_validate_json(await self.storage.read(snapshot_object))
        except Exception:
            # A missing/corrupt cache must not hide logs that are still retained.
            return None

    async def _save_evolution_snapshot(
        self,
        item: ExperimentRecord,
        run: OptimizationRunRecord,
        evolution: EvolutionResponse,
    ) -> None:
        object_name = self._optimization_artifact_name(item, run, "evolution.json")
        await self.storage.write(
            object_name,
            evolution.model_dump_json(indent=2).encode(),
            "application/json",
        )
        run.artifact_objects["evolution.json"] = object_name
        run.evolution_snapshot_prefix = run.cloud_artifact_prefix

    async def get_optimization_evolution(self, run_id: str, owner_id: str) -> EvolutionResponse:
        run = await self.repository.get_optimization_run(run_id)
        if run is None:
            raise AppError(404, "OPTIMIZATION_RUN_NOT_FOUND", "Optimization run was not found")
        item = await self._owned(run.experiment_id, owner_id)
        active_statuses = {
            ExperimentStatus.OPTIMIZATION_QUEUED,
            ExperimentStatus.OPTIMIZING,
            ExperimentStatus.CANDIDATE_EVALUATING,
        }
        cached_evolution = await self._load_evolution_snapshot(run)
        if cached_evolution is not None and run.status not in active_statuses:
            has_stale_pending = any(iteration.decision == "Pending" for iteration in cached_evolution.iterations)
            if not has_stale_pending:
                return cached_evolution
        if self.cloud_optimizer is None or not hasattr(self.cloud_optimizer, "evolution"):
            if cached_evolution is not None:
                return cached_evolution
            return EvolutionResponse(
                available=False,
                message="Evolution logs are only available for Cloud Run GEPA jobs.",
            )
        if not run.cloud_artifact_prefix:
            if cached_evolution is not None:
                return cached_evolution
            return EvolutionResponse(
                available=False,
                message="The Cloud Run execution has not started yet.",
            )
        current_evolution = await self.cloud_optimizer.evolution(
            run.cloud_artifact_prefix,
            started_at=run.started_at,
        )
        append_history = bool(
            cached_evolution is not None
            and run.evolution_snapshot_prefix
            and run.evolution_snapshot_prefix != run.cloud_artifact_prefix
        )
        evolution = (
            merge_evolution_history(cached_evolution, current_evolution) if append_history else current_evolution
        )
        if not current_evolution.available and cached_evolution is not None:
            evolution = cached_evolution
        if evolution.available and evolution.iterations and run.status not in active_statuses:
            try:
                await self._save_evolution_snapshot(item, run, evolution)
                await self.repository.save_optimization_run(run)
            except Exception:
                # Returning the parsed history is more important than caching it.
                pass
        return evolution

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
        if run is None:
            return
        if run.status == ExperimentStatus.OPTIMIZATION_SUCCEEDED:
            item = await self.repository.get(run.experiment_id)
            if item is not None:
                await self._materialize_cloud_comparison(item, run)
            return
        polling_cloud_job = run.status == ExperimentStatus.OPTIMIZING and run.cloud_artifact_prefix is not None
        if run.status != ExperimentStatus.OPTIMIZATION_QUEUED and not polling_cloud_job:
            return
        if not polling_cloud_job:
            run.status = ExperimentStatus.OPTIMIZING
            run.started_at = datetime.now(UTC)
            await self.repository.save_optimization_run(run)
        item = await self.repository.get(run.experiment_id)
        try:
            if item is None or self.cloud_optimizer is None:
                raise RuntimeError("Cloud GEPA optimizer is not configured")
            parent = self._baseline_for(item)
            if run.parent_prompt_digest != parent.digest():
                raise RuntimeError("The candidate-zero baseline prompt has changed")
            effective_max_concurrency = run.max_concurrency or item.settings.max_concurrency
            run.max_concurrency = effective_max_concurrency
            optimization_settings = item.settings.model_copy(update={"max_concurrency": effective_max_concurrency})
            if polling_cloud_job:
                result = await self.cloud_optimizer.collect(run.cloud_artifact_prefix)
                if result is None:
                    if run.cloud_deadline_at and datetime.now(UTC) >= run.cloud_deadline_at:
                        raise RuntimeError("Cloud Run GEPA job timed out")
                    await self.optimization_dispatcher.dispatch(run.id, delay_seconds=60)
                    return
            else:
                references = {target.key: target for target in item.targets}
                if set(item.target_function_ids) != set(references):
                    raise RuntimeError("The immutable target snapshot is incomplete")
                targets = {
                    split: [
                        OptimizationTarget(
                            id=target_key,
                            project=references[target_key].project,
                            symbol=references[target_key].symbol,
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
                        split="test",
                        source_file=references[target_key].source_file,
                    )
                    for target_key in item.dataset_splits["test"]
                ]
                if hasattr(self.cloud_optimizer, "start"):
                    start_options = {}
                    # Samples and uploaded projects share the same immutable
                    # evaluation-worker protocol.  Omitting sample snapshots
                    # here would silently fall back to executing their tests
                    # inside the GEPA coordinator.
                    if item.project_snapshots:
                        start_options["projects"] = item.project_snapshots
                    if run.resume_artifact_prefix:
                        start_options["resume_artifacts_prefix"] = run.resume_artifact_prefix
                    run.cloud_artifact_prefix = await self.cloud_optimizer.start(
                        baseline=parent,
                        train=targets["train"],
                        validation=targets["validation"],
                        holdout=holdout,
                        settings=optimization_settings,
                        vertexai_project=run.vertexai_project,
                        provider_secret_refs=run.provider_secret_refs,
                        **start_options,
                    )
                    run.cloud_deadline_at = datetime.now(UTC) + timedelta(seconds=self.cloud_optimizer.timeout_seconds)
                    await self.repository.save_optimization_run(run)
                    await self.optimization_dispatcher.dispatch(run.id, delay_seconds=60)
                    return
                result = await self.cloud_optimizer.optimize(
                    baseline=parent,
                    train=targets["train"],
                    validation=targets["validation"],
                    holdout=holdout,
                    settings=optimization_settings,
                    vertexai_project=run.vertexai_project,
                    projects=item.project_snapshots or None,
                )
            artifact_payloads = {
                "candidate_prompt.json": (result.candidate.as_json().encode(), "application/json"),
                "gepa_result.json": (
                    json.dumps(result.gepa_result, ensure_ascii=False, indent=2, default=str).encode(),
                    "application/json",
                ),
                "cost_report.json": (
                    json.dumps(result.gepa_result.get("cost_report", {}), ensure_ascii=False, indent=2).encode(),
                    "application/json",
                ),
            }
            if run.cloud_artifact_prefix and hasattr(self.cloud_optimizer, "evolution"):
                previous_evolution = await self._load_evolution_snapshot(run)
                current_evolution = await self.cloud_optimizer.evolution(
                    run.cloud_artifact_prefix,
                    started_at=run.started_at,
                )
                append_history = bool(
                    previous_evolution is not None
                    and run.evolution_snapshot_prefix
                    and run.evolution_snapshot_prefix != run.cloud_artifact_prefix
                )
                evolution = (
                    merge_evolution_history(previous_evolution, current_evolution)
                    if append_history
                    else current_evolution
                )
                if not current_evolution.available and previous_evolution is not None:
                    evolution = previous_evolution
                if evolution.available and evolution.iterations:
                    artifact_payloads["evolution.json"] = (
                        evolution.model_dump_json(indent=2).encode(),
                        "application/json",
                    )
                    run.evolution_snapshot_prefix = run.cloud_artifact_prefix
            artifact_objects = {}
            for name, (content, content_type) in artifact_payloads.items():
                object_name = self._optimization_artifact_name(item, run, name)
                await self.storage.write(object_name, content, content_type)
                artifact_objects[name] = object_name
            run.status = ExperimentStatus.OPTIMIZATION_SUCCEEDED
            run.candidate_prompt = result.candidate.as_candidate()
            run.candidate_prompt_digest = result.candidate.digest()
            run.baseline_validation_score = result.baseline_score
            run.candidate_validation_score = result.score
            run.candidate_count = result.candidate_count
            run.metric_calls = result.metric_calls
            run.final_validation = _compact_final_validation(result.gepa_result.get("final_validation", {}))
            run.cost_report = result.gepa_result.get("cost_report", {})
            total_cost = (run.cost_report.get("total") or {}).get("estimated_cost_usd", 0.0)
            run.estimated_cost_usd = float(total_cost or 0.0)
            raw_usage = (run.cost_report.get("total") or {}).get("token_usage", {})
            run.token_usage = {
                str(key): int(value)
                for key, value in raw_usage.items()
                if isinstance(value, int | float) and value >= 0
            }
            run.artifact_objects = artifact_objects
            run.finished_at = datetime.now(UTC)
            item.status = ExperimentStatus.OPTIMIZATION_SUCCEEDED
            item.updated_at = run.finished_at
        except OptimizationPausedError as exc:
            now = datetime.now(UTC)
            run.status = ExperimentStatus.PAUSED
            run.pause_reason = str(exc)[:1000]
            run.paused_at = now
            run.cloud_deadline_at = None
            run.error_message = None
            run.finished_at = None
            if item:
                item.status = ExperimentStatus.PAUSED
                item.updated_at = now
                if run.cloud_artifact_prefix and hasattr(self.cloud_optimizer, "evolution"):
                    try:
                        previous_evolution = await self._load_evolution_snapshot(run)
                        current_evolution = await self.cloud_optimizer.evolution(
                            run.cloud_artifact_prefix,
                            started_at=run.started_at,
                        )
                        append_history = bool(
                            previous_evolution is not None
                            and run.evolution_snapshot_prefix
                            and run.evolution_snapshot_prefix != run.cloud_artifact_prefix
                        )
                        evolution = (
                            merge_evolution_history(previous_evolution, current_evolution)
                            if append_history
                            else current_evolution
                        )
                        if not current_evolution.available and previous_evolution is not None:
                            evolution = previous_evolution
                        if evolution.available and evolution.iterations:
                            await self._save_evolution_snapshot(item, run, evolution)
                    except Exception:
                        # Pausing must succeed even if Cloud Logging is delayed.
                        pass
        except Exception as exc:
            now = datetime.now(UTC)
            if polling_cloud_job and self.optimization_dispatcher is not None and _is_transient_cloud_error(exc):
                # The Cloud Run execution may still be healthy. Persist the
                # non-terminal state before scheduling another collection pass.
                run.status = ExperimentStatus.OPTIMIZING
                run.error_message = None
                run.finished_at = None
                if item:
                    item.status = ExperimentStatus.OPTIMIZING
                    item.updated_at = now
                await self.repository.save_optimization_run(run)
                if item:
                    await self.repository.save(item)
                await self.optimization_dispatcher.dispatch(run.id, delay_seconds=60)
                return
            if run.resume_artifact_prefix and run.cloud_artifact_prefix is None:
                run.status = ExperimentStatus.PAUSED
                run.cloud_artifact_prefix = run.resume_artifact_prefix
                run.pause_reason = f"Resume execution could not start: {str(exc)[-900:]}"
                run.paused_at = now
                run.error_message = None
                run.finished_at = None
                if item:
                    item.status = ExperimentStatus.PAUSED
                    item.updated_at = now
            else:
                run.status = ExperimentStatus.FAILED
                run.error_message = str(exc)[-4000:]
                run.finished_at = now
                if item:
                    # A failed search does not invalidate candidate zero and may be retried.
                    item.status = ExperimentStatus.DRAFT
                    item.updated_at = run.finished_at
        await self.repository.save_optimization_run(run)
        if item:
            await self.repository.save(item)
        if item and run.status == ExperimentStatus.OPTIMIZATION_SUCCEEDED:
            await self._materialize_cloud_comparison(item, run)

    async def _materialize_cloud_comparison(
        self,
        item: ExperimentRecord,
        optimization: OptimizationRunRecord,
    ) -> ComparisonRunRecord:
        """Persist the paired result already produced inside the GEPA Cloud Run job.

        GEPA evaluates the immutable baseline as candidate zero and owns the locked
        final comparison. Creating another worker job here would only duplicate that
        work, so the API turns the existing final-validation artifact into the normal
        comparison/review records immediately.
        """
        if item.comparison_run_id:
            existing = await self.repository.get_comparison_run(item.comparison_run_id)
            if existing is not None:
                if existing.status == ExperimentStatus.COMPARISON_QUEUED:
                    await self.execute_comparison(existing.id)
                    return (await self.repository.get_comparison_run(existing.id)) or existing
                return existing
        if not optimization.final_validation:
            raise RuntimeError("Cloud GEPA final validation is unavailable")
        if not optimization.candidate_prompt or not optimization.candidate_prompt_digest:
            raise RuntimeError("The GEPA proposal prompt is unavailable")
        now = datetime.now(UTC)
        comparison = ComparisonRunRecord(
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
        if not comparison.test_target_ids:
            raise RuntimeError("The experiment has no locked test targets")
        await self.repository.create_comparison_run(comparison)
        item.status = ExperimentStatus.COMPARISON_QUEUED
        item.comparison_run_id = comparison.id
        item.updated_at = now
        await self.repository.save(item)
        await self.execute_comparison(comparison.id)
        return (await self.repository.get_comparison_run(comparison.id)) or comparison

    async def request_comparison(
        self,
        experiment_id: str,
        owner_id: str,
        *,
        full_access: bool = False,
    ) -> ComparisonRunResponse:
        item = await self._owned(experiment_id, owner_id)
        if item.comparison_run_id:
            existing = await self.repository.get_comparison_run(item.comparison_run_id)
            if existing is not None:
                return ComparisonRunResponse.model_validate(existing)
        await self._enforce_standard_account_concurrency(
            owner_id,
            full_access=full_access,
            exclude_experiment_id=item.id,
        )
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
            await self._ensure_baseline_prompt_snapshot(item)
            await self._ensure_optimized_prompt_snapshot(item, run)
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

    async def get_prompt_registry_entry(self, experiment_id: str, owner_id: str) -> PromptRegistryEntryResponse:
        item = await self._owned(experiment_id, owner_id)
        return await self._prompt_registry_entry(item)

    async def list_prompt_registry(self, owner_id: str, offset: int = 0, limit: int = 50) -> PromptRegistryListResponse:
        experiments = await self.repository.list_for_owner(owner_id)
        total = len(experiments)
        page = experiments[offset : offset + limit]
        return PromptRegistryListResponse(
            items=[await self._prompt_registry_entry(item) for item in page],
            total=total,
            offset=offset,
            limit=limit,
        )

    async def _prompt_registry_entry(self, item: ExperimentRecord) -> PromptRegistryEntryResponse:
        """Materialize immutable prompt snapshots for historical experiment records on read."""
        baseline = await self._ensure_baseline_prompt_snapshot(item)
        optimized = await self._ensure_optimized_prompt_snapshot(item)
        comparison = (
            await self.repository.get_comparison_run(item.comparison_run_id) if item.comparison_run_id else None
        )
        optimization = (
            await self.repository.get_optimization_run(item.optimization_run_id) if item.optimization_run_id else None
        )
        cost_report = optimization.cost_report if optimization else {}
        per_prompt_cost = cost_report.get("coverup_by_prompt") or {}
        baseline_cost = float((per_prompt_cost.get(baseline.prompt_digest) or {}).get("estimated_cost_usd") or 0.0)
        optimized_cost = float(optimization.estimated_cost_usd) if optimization else 0.0
        baseline_response = PromptSnapshotResponse.model_validate(baseline).model_copy(
            update={"estimated_cost_usd": baseline_cost}
        )
        optimized_response = (
            PromptSnapshotResponse.model_validate(optimized).model_copy(update={"estimated_cost_usd": optimized_cost})
            if optimized
            else None
        )
        project_names = [snapshot.name for snapshot in item.project_snapshots] or list(item.project_ids)
        return PromptRegistryEntryResponse(
            experiment_id=item.id,
            experiment_name=item.name,
            project_ids=list(item.project_ids),
            project_names=project_names,
            status=item.status,
            baseline=baseline_response,
            optimized=optimized_response,
            baseline_metrics=self._coverage_metrics(comparison.baseline_metrics if comparison else None),
            optimized_metrics=optimized.metrics if optimized else PromptCoverageMetrics(),
            absolute_gain=comparison.absolute_gain if comparison else None,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    @staticmethod
    def _test_generation_settings(item: ExperimentRecord, payload: CreateTestGenerationRequest) -> dict:
        """Freeze the effective CoverUp settings into the immutable run document."""
        return {
            "max_attempts": payload.max_attempts or item.settings.max_attempts,
            "repeat_tests": item.settings.repeat_tests if payload.repeat_tests is None else payload.repeat_tests,
            "max_concurrency": payload.max_concurrency or item.settings.max_concurrency,
            "rate_limit": payload.rate_limit if payload.rate_limit is not None else item.settings.rate_limit,
            "pytest_args": item.settings.pytest_args,
            "random_seed": payload.random_seed,
        }

    @staticmethod
    def _select_legacy_test_generation_targets(
        item: ExperimentRecord, payload: CreateTestGenerationRequest
    ) -> list[TargetReference]:
        if payload.scope == TestGenerationScope.PROJECT:
            selected = list(item.targets)
        elif payload.scope == TestGenerationScope.MODULES:
            wanted = set(payload.source_files)
            selected = [target for target in item.targets if target.source_file in wanted]
        else:
            wanted = set(payload.function_ids)
            selected = [target for target in item.targets if target.function_id in wanted]
        if not selected:
            raise AppError(422, "TEST_GENERATION_SCOPE_EMPTY", "The selected test-generation scope has no targets")
        selected_keys = {target.key for target in selected}
        if len(selected_keys) != len(selected):
            raise AppError(409, "TARGET_SNAPSHOT_INVALID", "The experiment contains duplicate immutable targets")
        return selected

    async def _select_configured_test_generation_targets(
        self, item: ExperimentRecord, owner_id: str, payload: CreateTestGenerationRequest
    ) -> list[TargetReference]:
        """Build a fresh, immutable final-suite target snapshot from the selected projects.

        An experiment's prompt is reusable for every analyzed function in the
        projects that produced that prompt; it is not limited to the smaller
        train/validation/test sample used by GEPA.
        """
        selected_project_ids = payload.project_ids or list(item.project_ids)
        snapshots = {snapshot.project_id: snapshot for snapshot in item.project_snapshots}
        unknown = sorted(set(selected_project_ids) - set(snapshots))
        if unknown:
            raise AppError(
                422,
                "TEST_GENERATION_PROJECT_NOT_IN_EXPERIMENT",
                "A test suite can only use projects from the selected prompt's experiment",
            )
        available: dict[str, TargetReference] = {}
        for project_id in selected_project_ids:
            project = await self.projects.require_owned(project_id, owner_id)
            snapshot = snapshots[project_id]
            for function in await self._list_functions(project_id):
                if not is_valid_optimization_function(function):
                    continue
                source_file = self._runner_source_file(project, function.file)
                if source_file is None:
                    continue
                target = TargetReference(
                    project_id=project_id,
                    function_id=function.id,
                    project=snapshot.runner_project,
                    source_file=source_file,
                    symbol=function.qualified_name,
                    statements=function.statements,
                    branches=function.branches,
                    loc=function.loc,
                )
                available[target.key] = target
        if not available:
            raise AppError(422, "TEST_GENERATION_SCOPE_EMPTY", "No valid functions are available")
        try:
            if payload.sampling_method == SamplingMethod.MANUAL:
                selected_keys = set(payload.function_ids)
                missing = selected_keys - set(available)
                if missing:
                    raise ValueError(f"Unknown selected functions: {', '.join(sorted(missing)[:10])}")
                selected = [available[key] for key in payload.function_ids]
            else:
                selected = select_targets(
                    available.values(), payload.sampling_method, payload.random_seed, payload.function_count
                )
        except ValueError as exc:
            raise AppError(422, "INVALID_TEST_GENERATION_SELECTION", str(exc)) from exc
        if not selected:
            raise AppError(422, "TEST_GENERATION_SCOPE_EMPTY", "The selected test-suite scope has no targets")
        return selected

    async def _require_test_generation_projects(
        self, item: ExperimentRecord, owner_id: str, project_ids: list[str] | None = None
    ) -> None:
        """Confirm the immutable project snapshots still have executable source/runtime inputs."""
        selected = set(project_ids or item.project_ids)
        for snapshot in item.project_snapshots:
            if snapshot.project_id not in selected:
                continue
            project = await self.projects.require_owned(snapshot.project_id, owner_id)
            if self.projects.is_sample(project.id):
                continue
            if not snapshot.archive_object or not snapshot.runtime_bundle_object:
                raise AppError(
                    409,
                    "TEST_GENERATION_RUNTIME_UNAVAILABLE",
                    "The uploaded project snapshot has no prepared runtime bundle",
                )

    async def request_test_generation(
        self,
        experiment_id: str,
        owner_id: str,
        payload: CreateTestGenerationRequest,
    ) -> TestGenerationRunResponse:
        item = await self._owned(experiment_id, owner_id)
        requested_project_ids = payload.project_ids or list(item.project_ids)
        await self._require_test_generation_projects(item, owner_id, requested_project_ids)
        snapshot = await self.repository.get_prompt_snapshot(item.id, payload.prompt_role)
        if snapshot is None:
            if payload.prompt_role == PromptRole.BASELINE:
                snapshot = await self._ensure_baseline_prompt_snapshot(item)
            else:
                snapshot = await self._ensure_optimized_prompt_snapshot(item)
        if snapshot is None:
            raise AppError(
                409,
                "OPTIMIZED_PROMPT_NOT_READY",
                "An optimized prompt is available only after the experiment final comparison finishes",
            )
        configured_selection = (
            bool(payload.project_ids)
            or payload.function_count is not None
            or payload.sampling_method != SamplingMethod.RANDOM
        )
        targets = (
            await self._select_configured_test_generation_targets(item, owner_id, payload)
            if configured_selection
            else self._select_legacy_test_generation_targets(item, payload)
        )
        settings = self._test_generation_settings(item, payload)
        model = payload.model or snapshot.coverup_model
        if self.test_generation_dispatcher is None:
            raise RuntimeError("Test-generation dispatcher is not configured")
        # An idempotency key protects a browser retry/double-click while preserving
        # the separate immutable history of deliberate regenerate requests.
        if payload.idempotency_key:
            for existing in await self.repository.list_test_generation_runs_for_owner(owner_id):
                if existing.idempotency_key == payload.idempotency_key:
                    if existing.experiment_id != item.id or existing.prompt_digest != snapshot.prompt_digest:
                        raise AppError(409, "IDEMPOTENCY_KEY_REUSED", "Idempotency key belongs to a different request")
                    return TestGenerationRunResponse.model_validate(existing)
        provider_secret_refs = {}
        if self.provider_credentials is not None:
            provider_secret_refs = await self.provider_credentials.resolve_for_models(owner_id, [model])
        now = datetime.now(UTC)
        run = TestGenerationRunRecord(
            id=new_id(),
            owner_id=owner_id,
            experiment_id=item.id,
            name=payload.name.strip(),
            prompt_snapshot_id=snapshot.id,
            prompt_digest=snapshot.prompt_digest,
            prompt_role=snapshot.role,
            status=TestGenerationStatus.QUEUED,
            project_ids=list(dict.fromkeys(target.project_id for target in targets)),
            sampling_method=payload.sampling_method,
            runtime_environment_id=next(
                (
                    project_snapshot.runtime_environment_id
                    for project_snapshot in item.project_snapshots
                    if project_snapshot.project_id in requested_project_ids
                ),
                None,
            ),
            source_snapshot_digest=snapshot.source_snapshot_digest,
            dataset_digest=snapshot.dataset_digest,
            scope=payload.scope,
            source_files=list(payload.source_files),
            function_ids=list(payload.function_ids),
            target_ids=[target.key for target in targets],
            model=model,
            random_seed=settings["random_seed"],
            repeat_tests=settings["repeat_tests"],
            max_attempts=settings["max_attempts"],
            max_concurrency=settings["max_concurrency"],
            rate_limit=settings["rate_limit"],
            cost_ceiling_usd=payload.cost_ceiling_usd,
            runner_protocol_version=snapshot.runner_protocol_version,
            idempotency_key=payload.idempotency_key,
            provider_secret_refs={
                environment: {"secret": reference.secret, "version": reference.version}
                for environment, reference in provider_secret_refs.items()
            },
            target_snapshots=targets,
            created_at=now,
        )
        await self.repository.create_test_generation_run(run)
        try:
            await self.test_generation_dispatcher.dispatch(run.id)
        except Exception as exc:
            run.status = TestGenerationStatus.FAILED
            run.error_message = "Test-generation job could not be queued"
            run.finished_at = datetime.now(UTC)
            await self.repository.save_test_generation_run(run)
            raise AppError(503, "TEST_GENERATION_QUEUE_UNAVAILABLE", "Test generation could not be queued") from exc
        stored = await self.repository.get_test_generation_run(run.id)
        return TestGenerationRunResponse.model_validate(stored or run)

    async def get_test_generation_run(self, run_id: str, owner_id: str) -> TestGenerationRunResponse:
        run = await self.repository.get_test_generation_run(run_id)
        if run is None or run.owner_id != owner_id:
            raise AppError(404, "TEST_GENERATION_RUN_NOT_FOUND", "Test generation run was not found")
        return TestGenerationRunResponse.model_validate(run)

    async def delete_test_generation_run(self, run_id: str, owner_id: str) -> None:
        run = await self.repository.get_test_generation_run(run_id)
        if run is None or run.owner_id != owner_id:
            raise AppError(404, "TEST_GENERATION_RUN_NOT_FOUND", "Test generation run was not found")
        if run.status in {
            TestGenerationStatus.QUEUED,
            TestGenerationStatus.PREPARING,
            TestGenerationStatus.GENERATING,
            TestGenerationStatus.RUNNING_TESTS,
        }:
            raise AppError(409, "TEST_GENERATION_ACTIVE", "A running test suite cannot be deleted")
        await self.repository.delete_test_generation_run(run.id)

    async def list_test_generation_runs(
        self, owner_id: str, offset: int = 0, limit: int = 50
    ) -> TestGenerationRunListResponse:
        runs = await self.repository.list_test_generation_runs_for_owner(owner_id)
        return TestGenerationRunListResponse(
            items=[TestGenerationRunResponse.model_validate(run) for run in runs[offset : offset + limit]],
            total=len(runs),
            offset=offset,
            limit=limit,
        )

    async def get_test_generation_artifact(self, run_id: str, artifact_name: str, owner_id: str) -> bytes:
        run = await self.repository.get_test_generation_run(run_id)
        if run is None or run.owner_id != owner_id:
            raise AppError(404, "TEST_GENERATION_RUN_NOT_FOUND", "Test generation run was not found")
        object_name = run.artifact_objects.get(artifact_name)
        if object_name is None:
            raise AppError(404, "ARTIFACT_NOT_FOUND", "Artifact was not found in this final test-generation run")
        return await self.storage.read(object_name)

    async def get_test_generation_manifest(self, run_id: str, owner_id: str) -> dict:
        """Return the small, redacted result manifest for the run detail viewer.

        This deliberately does not turn arbitrary storage paths into browser-viewable files.
        Individual source and generated test files will require a validated artifact index.
        """
        content = await self.get_test_generation_artifact(run_id, "manifest", owner_id)
        if len(content) > MAX_TEST_GENERATION_MANIFEST_BYTES:
            raise AppError(413, "ARTIFACT_TOO_LARGE", "Test-generation manifest is too large to view")
        try:
            manifest = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AppError(422, "INVALID_ARTIFACT", "Test-generation manifest is not valid JSON") from exc
        if not isinstance(manifest, dict):
            raise AppError(422, "INVALID_ARTIFACT", "Test-generation manifest must be a JSON object")
        return _redact_artifact_value(manifest)

    async def get_test_generation_text_artifact(self, run_id: str, artifact_name: str, owner_id: str) -> dict[str, str]:
        """Return an indexed generated test, source module, or coverage report as bounded UTF-8 text."""
        if not re.fullmatch(r"file-(generated-test|source|coverage)-[1-9][0-9]*", artifact_name):
            raise AppError(404, "ARTIFACT_NOT_FOUND", "Text artifact was not found in this final test-generation run")
        content = await self.get_test_generation_artifact(run_id, artifact_name, owner_id)
        if len(content) > MAX_TEST_GENERATION_MANIFEST_BYTES:
            raise AppError(413, "ARTIFACT_TOO_LARGE", "Text artifact is too large to view")
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AppError(422, "INVALID_ARTIFACT", "Text artifact is not valid UTF-8") from exc
        return {"artifact_name": artifact_name, "content": text}

    async def execute_test_generation(self, run_id: str) -> None:
        run = await self.repository.get_test_generation_run(run_id)
        if run is None:
            return
        polling_cloud_job = run.status == TestGenerationStatus.GENERATING and run.cloud_artifact_prefix is not None
        if run.status != TestGenerationStatus.QUEUED and not polling_cloud_job:
            return
        if not polling_cloud_job:
            run.status = TestGenerationStatus.PREPARING
            run.started_at = datetime.now(UTC)
            await self.repository.save_test_generation_run(run)
        try:
            item = await self.repository.get(run.experiment_id)
            if item is None or item.owner_id != run.owner_id:
                raise RuntimeError("Experiment is unavailable")
            snapshot = await self.repository.get_prompt_snapshot(item.id, run.prompt_role)
            if snapshot is None or snapshot.id != run.prompt_snapshot_id or snapshot.prompt_digest != run.prompt_digest:
                raise RuntimeError("Immutable prompt snapshot is unavailable")
            targets_by_id = {target.key: target for target in item.targets}
            targets_by_id.update({target.key: target for target in run.target_snapshots})
            targets = [targets_by_id[target_id] for target_id in run.target_ids if target_id in targets_by_id]
            if len(targets) != len(run.target_ids):
                raise RuntimeError("The immutable target snapshot is incomplete")
            if self.cloud_test_generator is None:
                raise RuntimeError("Cloud Run final test generator is not configured")
            if polling_cloud_job:
                result = await self.cloud_test_generator.collect(run.cloud_artifact_prefix)
                if result is None:
                    if run.cloud_deadline_at and datetime.now(UTC) >= run.cloud_deadline_at:
                        run.status = TestGenerationStatus.TIMED_OUT
                        run.error_message = "Cloud Run final test-generation job timed out"
                        run.finished_at = datetime.now(UTC)
                        await self.repository.save_test_generation_run(run)
                        return
                    assert self.test_generation_dispatcher is not None
                    await self.test_generation_dispatcher.dispatch(run.id, delay_seconds=30)
                    return
            else:
                run.status = TestGenerationStatus.GENERATING
                await self.repository.save_test_generation_run(run)
                run.cloud_artifact_prefix = await self.cloud_test_generator.start(
                    prompt=snapshot.prompt,
                    targets=[
                        {"project": target.project, "source_file": target.source_file, "symbol": target.symbol}
                        for target in targets
                    ],
                    model=run.model,
                    settings={
                        "max_attempts": run.max_attempts,
                        "repeat_tests": run.repeat_tests,
                        "max_concurrency": run.max_concurrency,
                        "rate_limit": run.rate_limit,
                        "pytest_args": item.settings.pytest_args,
                        "random_seed": run.random_seed,
                    },
                    projects=[
                        project_snapshot
                        for project_snapshot in item.project_snapshots
                        if project_snapshot.project_id in run.project_ids
                    ]
                    or None,
                    provider_secret_refs=run.provider_secret_refs,
                )
                run.cloud_deadline_at = datetime.now(UTC) + timedelta(seconds=self.cloud_test_generator.timeout_seconds)
                await self.repository.save_test_generation_run(run)
                assert self.test_generation_dispatcher is not None
                await self.test_generation_dispatcher.dispatch(run.id, delay_seconds=30)
                return
            metrics = TestGenerationMetrics.model_validate(result.get("metrics") or {})
            artifacts = result.get("artifacts") or {}
            prefix = run.cloud_artifact_prefix.rstrip("/")
            run.metrics = metrics
            run.estimated_cost_usd = float(result.get("estimated_cost_usd") or 0.0)
            raw_usage = result.get("token_usage") or {}
            run.token_usage = {
                str(key): int(value)
                for key, value in raw_usage.items()
                if isinstance(value, int | float) and value >= 0
            }
            run.artifact_objects = _validated_final_test_artifact_objects(prefix, artifacts)
            run.status = (
                TestGenerationStatus.PARTIAL if result.get("status") == "partial" else TestGenerationStatus.COMPLETED
            )
            run.finished_at = datetime.now(UTC)
        except Exception as exc:
            run.status = TestGenerationStatus.FAILED
            run.error_message = str(exc)[-4000:]
            run.finished_at = datetime.now(UTC)
        await self.repository.save_test_generation_run(run)

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

    @staticmethod
    def _optimization_artifact_name(
        item: ExperimentRecord,
        run: OptimizationRunRecord,
        name: str,
    ) -> str:
        return f"artifacts/{item.owner_id}/{item.id}/{run.id}/{name}"

    async def _list_functions(self, project_id: str):
        if self.samples and self.samples.contains(project_id):
            return self.samples.functions(project_id)
        return await self.functions.list_for_project(project_id)

    @staticmethod
    def _runner_project_name(project, index: int, used: set[str]) -> str:
        base = re.sub(r"[^A-Za-z0-9_.-]+", "-", project.name.lower()).strip(".-") or f"project-{index + 1}"
        candidate = base
        suffix = 2
        while candidate in used:
            candidate = f"{base}-{suffix}"
            suffix += 1
        return candidate

    def _runner_source_file(self, project, source_file: str) -> str | None:
        if self.projects.is_sample(project.id):
            return source_file
        return normalize_optimization_source_file(project.settings.runtime.source_directory, source_file)

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
