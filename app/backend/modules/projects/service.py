from datetime import UTC, datetime
from uuid import uuid4

from backend.core.errors import AppError
from backend.modules.analysis.repository import FunctionRepository
from backend.modules.projects.repository import ProjectRepository
from backend.modules.projects.schemas import (
    CreateProjectRequest,
    FailureStage,
    ProjectListResponse,
    ProjectRecord,
    ProjectResponse,
    ProjectSettings,
    ProjectSettingsPatch,
    ProjectStatus,
    RuntimeCapabilitiesResponse,
    RuntimeCapability,
    RuntimeRolloutStatusResponse,
    RuntimeStatus,
    ValidateProjectSettingsResponse,
)
from backend.modules.uploads.service import UploadService

from .samples import SampleProjectCatalog


class ProjectService:
    def __init__(
        self,
        repository: ProjectRepository,
        uploads: UploadService,
        samples: SampleProjectCatalog | None = None,
        functions: FunctionRepository | None = None,
    ):
        self.repository = repository
        self.uploads = uploads
        self.samples = samples
        self.functions = functions
        self.runtime = None

    def set_runtime_service(self, runtime) -> None:
        self.runtime = runtime

    async def create(self, owner_id: str, payload: CreateProjectRequest) -> ProjectResponse:
        upload = await self.uploads.require_ready(payload.upload_id, owner_id)
        if upload.requested_python_version != payload.settings.runtime.python_version:
            raise AppError(
                409,
                "UPLOAD_SETTINGS_MISMATCH",
                "The project Python version differs from the validated upload settings",
            )
        environment_id = payload.runtime_environment_id or uuid4().hex
        if environment_id == "sample-runtime":
            raise AppError(
                422,
                "SAMPLE_RUNTIME_READ_ONLY",
                "Uploaded projects cannot join the bundled sample environment",
            )
        environment_name = payload.runtime_environment_name or f"{payload.name} environment"
        if payload.runtime_environment_id:
            existing_members = [
                item
                for item in await self.repository.list_for_owner(owner_id)
                if item.runtime_environment_id == environment_id
            ]
            if not existing_members:
                raise AppError(
                    422,
                    "RUNTIME_ENVIRONMENT_NOT_FOUND",
                    "The selected runtime environment does not exist",
                )
            environment_name = existing_members[0].runtime_environment_name or environment_name
            expected_python = existing_members[0].settings.runtime.python_version
            if payload.settings.runtime.python_version != expected_python:
                raise AppError(
                    409,
                    "PYTHON_VERSION_CONFLICT",
                    f"This environment uses Python {expected_python}",
                )
        now = datetime.now(UTC)
        project = ProjectRecord(
            id=str(uuid4()),
            owner_id=owner_id,
            name=payload.name,
            description=payload.description,
            upload_id=upload.id,
            object_name=upload.object_name,
            branch=payload.branch,
            commit=payload.commit,
            runtime_environment_id=environment_id,
            runtime_environment_name=environment_name,
            status=ProjectStatus.UPLOADED,
            settings=payload.settings,
            requested_python_version=payload.settings.runtime.python_version,
            created_at=now,
            updated_at=now,
        )
        await self.repository.create(project)
        return self._response(project)

    async def list(self, owner_id: str) -> ProjectListResponse:
        projects = await self.repository.list_for_owner(owner_id)
        if self.runtime:
            projects = [await self.runtime.refresh(project) for project in projects]
        return ProjectListResponse(items=[self._response(project) for project in projects], total=len(projects))

    async def list_samples(self, owner_id: str) -> ProjectListResponse:
        projects = self.samples.list(owner_id) if self.samples else []
        return ProjectListResponse(items=[self._response(project) for project in projects], total=len(projects))

    async def get(self, project_id: str, owner_id: str) -> ProjectResponse:
        project = await self.require_owned(project_id, owner_id)
        if self.runtime and not self.is_sample(project_id):
            project = await self.runtime.refresh(project)
        return self._response(project)

    async def prepare_runtime(self, project_id: str, owner_id: str) -> ProjectResponse:
        if self.is_sample(project_id):
            raise AppError(409, "SAMPLE_PROJECT_READ_ONLY", "Bundled samples already have a runtime")
        project = await self.require_owned(project_id, owner_id)
        if project.status not in {ProjectStatus.READY, ProjectStatus.WARNING}:
            raise AppError(409, "ANALYSIS_NOT_READY", "Static analysis must complete first")
        if self.runtime is None:
            raise AppError(503, "RUNTIME_PREPARER_UNAVAILABLE", "Runtime preparation is not configured")
        return await self.runtime.request(project)

    async def retry_runtime_build(self, project_id: str, owner_id: str) -> ProjectResponse:
        project = await self.require_owned(project_id, owner_id)
        report = project.runtime_report
        if (
            project.runtime_status != RuntimeStatus.FAILED
            or report is None
            or not report.retryable
            or report.failure_stage
            not in {
                FailureStage.METADATA,
                FailureStage.RESOLVE,
                FailureStage.BUILD,
                FailureStage.INTERNAL,
            }
        ):
            raise AppError(
                409, "RUNTIME_BUILD_NOT_RETRYABLE", "Fix the project settings or dependencies before rebuilding"
            )
        if self.runtime is None:
            raise AppError(503, "RUNTIME_PREPARER_UNAVAILABLE", "Runtime preparation is not configured")
        return await self.runtime.request(project)

    async def retry_runtime_execution(self, project_id: str, owner_id: str) -> ProjectResponse:
        project = await self.require_owned(project_id, owner_id)
        report = project.runtime_report
        if (
            project.runtime_status != RuntimeStatus.FAILED
            or report is None
            or not report.retryable
            or report.failure_stage not in {FailureStage.COLLECT, FailureStage.TEST, FailureStage.COVERAGE}
        ):
            raise AppError(409, "RUNTIME_EXECUTION_NOT_RETRYABLE", "This runtime failure cannot be retried")
        if self.runtime is None:
            raise AppError(503, "RUNTIME_PREPARER_UNAVAILABLE", "Runtime preparation is not configured")
        # The active bundle is deliberately left untouched. Runners that expose
        # an execution-only retry may reuse it; the legacy runner safely creates
        # a candidate and only activates it after admission succeeds.
        retry_execution = getattr(self.runtime, "retry_execution", None)
        if retry_execution is not None:
            return await retry_execution(project)
        return await self.runtime.request(project)

    def runtime_capabilities(self) -> RuntimeCapabilitiesResponse:
        runner = self.runtime.runner if self.runtime is not None else None
        health_check = getattr(runner, "is_healthy", None)
        healthy = bool(runner is not None and (health_check() if health_check is not None else True))
        image = getattr(runner, "image", "promptopt-sandbox:py3.12")
        versions = sorted(getattr(runner, "advertised_python_versions", ()) or {"3.12"})
        return RuntimeCapabilitiesResponse(
            items=[
                RuntimeCapability(
                    python_version=version,
                    image=image,
                    job=getattr(runner, "job_name", "promptopt-runtime-preparer"),
                    healthy=healthy,
                )
                for version in versions
            ]
        )

    def runtime_rollout_status(self) -> RuntimeRolloutStatusResponse:
        runner = self.runtime.runner if self.runtime is not None else None
        policy = getattr(runner, "policy", None)
        metrics = getattr(runner, "metrics", None)
        return RuntimeRolloutStatusResponse(
            enabled=bool(policy and policy.enabled),
            mode=policy.mode.value if policy else "disabled",
            canary_percent=policy.canary_percent if policy else 0,
            canary_python_versions=sorted(policy.canary_python_versions) if policy else [],
            advertised_python_versions=sorted(getattr(runner, "advertised_python_versions", ())),
            metrics=metrics.snapshot() if metrics else {},
        )

    async def validate_settings(
        self,
        project_id: str,
        owner_id: str,
        patch: ProjectSettingsPatch,
    ) -> ValidateProjectSettingsResponse:
        project = await self.require_owned(project_id, owner_id)
        settings = self._merged_settings(project.settings, patch)
        capabilities = self.runtime_capabilities().items
        if not any(item.healthy and item.python_version == settings.runtime.python_version for item in capabilities):
            raise AppError(
                422,
                "PYTHON_RUNTIME_UNAVAILABLE",
                f"Python {settings.runtime.python_version} does not have a healthy sandbox image/job",
            )
        return ValidateProjectSettingsResponse(settings=settings)

    async def update_settings(
        self,
        project_id: str,
        owner_id: str,
        patch: ProjectSettingsPatch,
    ) -> ProjectResponse:
        if self.samples and self.samples.contains(project_id):
            raise AppError(409, "SAMPLE_PROJECT_READ_ONLY", "Bundled sample settings are immutable")
        project = await self.require_owned(project_id, owner_id)
        updates = patch.model_dump(exclude_none=True)
        if not updates:
            raise AppError(400, "EMPTY_SETTINGS_PATCH", "Provide at least one settings section")
        project.settings = self._merged_settings(project.settings, patch)
        project.requested_python_version = project.settings.runtime.python_version
        project.updated_at = datetime.now(UTC)
        await self.repository.save(project)
        if (
            self.runtime is not None
            and self.runtime.runner is not None
            and project.status in {ProjectStatus.READY, ProjectStatus.WARNING}
        ):
            return await self.runtime.request(project)
        return self._response(project)

    async def delete(self, project_id: str, owner_id: str) -> None:
        if self.is_sample(project_id):
            raise AppError(409, "SAMPLE_PROJECT_READ_ONLY", "Bundled samples cannot be deleted")
        project = await self.require_owned(project_id, owner_id)
        if project.status == ProjectStatus.ANALYZING or project.runtime_status in {
            RuntimeStatus.QUEUED,
            RuntimeStatus.PREPARING,
        }:
            raise AppError(409, "PROJECT_BUSY", "Wait for the active project operation to finish")
        if self.functions is not None:
            await self.functions.delete_for_project(project.id)
        owner_projects = await self.repository.list_for_owner(owner_id)
        if not any(item.id != project.id and item.upload_id == project.upload_id for item in owner_projects):
            await self.uploads.delete(project.upload_id, owner_id)
        await self.repository.delete(project.id)

    async def require_owned(self, project_id: str, owner_id: str) -> ProjectRecord:
        if self.samples and (sample := self.samples.get(project_id, owner_id)):
            return sample
        project = await self.repository.get(project_id)
        if project is None or project.owner_id != owner_id:
            raise AppError(404, "PROJECT_NOT_FOUND", "Project was not found")
        return project

    async def read_archive(self, project: ProjectRecord, storage) -> bytes:
        if self.samples and self.samples.contains(project.id):
            return self.samples.archive(project.id)
        return await storage.read(project.object_name)

    def is_sample(self, project_id: str) -> bool:
        return bool(self.samples and self.samples.contains(project_id))

    @staticmethod
    def _response(project: ProjectRecord) -> ProjectResponse:
        return ProjectResponse.model_validate(project.model_dump(exclude={"owner_id"}))

    @staticmethod
    def _merged_settings(settings: ProjectSettings, patch: ProjectSettingsPatch) -> ProjectSettings:
        current = settings.model_dump()
        for section, values in patch.model_dump(exclude_none=True).items():
            current[section].update(values)
        return ProjectSettings.model_validate(current)
