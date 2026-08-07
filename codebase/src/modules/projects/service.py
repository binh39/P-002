from datetime import UTC, datetime
from uuid import uuid4

from src.core.errors import AppError
from src.modules.projects.repository import ProjectRepository
from src.modules.projects.schemas import (
    CreateProjectRequest,
    ProjectListResponse,
    ProjectRecord,
    ProjectResponse,
    ProjectSettings,
    ProjectSettingsPatch,
    ProjectStatus,
)
from src.modules.uploads.service import UploadService

from .samples import SampleProjectCatalog


class ProjectService:
    def __init__(
        self,
        repository: ProjectRepository,
        uploads: UploadService,
        samples: SampleProjectCatalog | None = None,
    ):
        self.repository = repository
        self.uploads = uploads
        self.samples = samples

    async def create(self, owner_id: str, payload: CreateProjectRequest) -> ProjectResponse:
        upload = await self.uploads.require_ready(payload.upload_id, owner_id)
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
            status=ProjectStatus.UPLOADED,
            settings=payload.settings,
            created_at=now,
            updated_at=now,
        )
        await self.repository.create(project)
        return self._response(project)

    async def list(self, owner_id: str) -> ProjectListResponse:
        projects = await self.repository.list_for_owner(owner_id)
        return ProjectListResponse(items=[self._response(project) for project in projects], total=len(projects))

    async def list_samples(self, owner_id: str) -> ProjectListResponse:
        projects = self.samples.list(owner_id) if self.samples else []
        return ProjectListResponse(items=[self._response(project) for project in projects], total=len(projects))

    async def get(self, project_id: str, owner_id: str) -> ProjectResponse:
        return self._response(await self.require_owned(project_id, owner_id))

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
        return self._response(project)

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
