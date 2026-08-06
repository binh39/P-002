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


class ProjectService:
    def __init__(self, repository: ProjectRepository, uploads: UploadService):
        self.repository = repository
        self.uploads = uploads

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

    async def get(self, project_id: str, owner_id: str) -> ProjectResponse:
        return self._response(await self.require_owned(project_id, owner_id))

    async def update_settings(
        self,
        project_id: str,
        owner_id: str,
        patch: ProjectSettingsPatch,
    ) -> ProjectResponse:
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
        project = await self.repository.get(project_id)
        if project is None or project.owner_id != owner_id:
            raise AppError(404, "PROJECT_NOT_FOUND", "Project was not found")
        return project

    @staticmethod
    def _response(project: ProjectRecord) -> ProjectResponse:
        return ProjectResponse.model_validate(project.model_dump(exclude={"owner_id"}))
