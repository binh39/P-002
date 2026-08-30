from datetime import UTC, datetime
from uuid import uuid4

from backend.core.errors import AppError
from backend.modules.analysis.repository import FunctionRepository
from backend.modules.projects.repository import ProjectRepository
from backend.modules.projects.schemas import (
    CreateProjectRequest,
    ProjectListResponse,
    ProjectRecord,
    ProjectResponse,
    ProjectSettings,
    ProjectSettingsPatch,
    ProjectStatus,
    RuntimeStatus,
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

    async def create(
        self, owner_id: str, payload: CreateProjectRequest, workspace_id: str | None = None
    ) -> ProjectResponse:
        upload = await self.uploads.require_ready(payload.upload_id, owner_id)
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
        now = datetime.now(UTC)
        project = ProjectRecord(
            id=str(uuid4()),
            owner_id=owner_id,
            workspace_id=workspace_id or owner_id,
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
            created_at=now,
            updated_at=now,
        )
        await self.repository.create(project)
        return self._response(project)

    async def list(self, owner_id: str, workspace_id: str | None = None) -> ProjectListResponse:
        projects = (
            await self.repository.list_for_workspace(workspace_id)
            if workspace_id
            else await self.repository.list_for_owner(owner_id)
        )
        if self.runtime:
            projects = [await self.runtime.refresh(project) for project in projects]
        return ProjectListResponse(items=[self._response(project) for project in projects], total=len(projects))

    async def list_samples(self, owner_id: str) -> ProjectListResponse:
        projects = self.samples.list(owner_id) if self.samples else []
        return ProjectListResponse(items=[self._response(project) for project in projects], total=len(projects))

    async def get(self, project_id: str, owner_id: str, workspace_id: str | None = None) -> ProjectResponse:
        project = await self.require_owned(project_id, owner_id, workspace_id)
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
        current = project.settings.model_dump()
        for section, values in updates.items():
            current[section].update(values)
        project.settings = ProjectSettings.model_validate(current)
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

    async def require_owned(self, project_id: str, owner_id: str, workspace_id: str | None = None) -> ProjectRecord:
        if self.samples and (sample := self.samples.get(project_id, owner_id)):
            return sample
        project = await self.repository.get(project_id)
        if project is None or (
            project.owner_id != owner_id and (project.workspace_id or project.owner_id) != workspace_id
        ):
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
        return ProjectResponse.model_validate(project.model_dump(exclude={"owner_id", "workspace_id"}))
