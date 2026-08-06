import asyncio
from datetime import UTC, datetime

from src.core.errors import AppError
from src.infrastructure.storage import ObjectStorage
from src.modules.analysis.analyzer import analyze_zip
from src.modules.analysis.dispatcher import AnalysisDispatcher
from src.modules.analysis.repository import FunctionRepository
from src.modules.analysis.schemas import (
    FunctionSourceResponse,
    ProjectFunctionListResponse,
    ProjectFunctionResponse,
)
from src.modules.projects.repository import ProjectRepository
from src.modules.projects.schemas import ProjectResponse, ProjectStatus
from src.modules.projects.service import ProjectService


class AnalysisService:
    def __init__(
        self,
        project_repository: ProjectRepository,
        function_repository: FunctionRepository,
        project_service: ProjectService,
        storage: ObjectStorage,
        max_python_files: int,
        max_uncompressed_bytes: int,
    ):
        self.projects = project_repository
        self.functions = function_repository
        self.project_service = project_service
        self.storage = storage
        self.max_python_files = max_python_files
        self.max_uncompressed_bytes = max_uncompressed_bytes
        self.dispatcher: AnalysisDispatcher | None = None

    def set_dispatcher(self, dispatcher: AnalysisDispatcher) -> None:
        self.dispatcher = dispatcher

    async def request(self, project_id: str, owner_id: str) -> ProjectResponse:
        project = await self.project_service.require_owned(project_id, owner_id)
        if self.dispatcher is None:
            raise RuntimeError("Analysis dispatcher is not configured")
        if project.status == ProjectStatus.ANALYZING:
            raise AppError(409, "ANALYSIS_ALREADY_RUNNING", "Project analysis is already running")
        project.status = ProjectStatus.ANALYZING
        project.updated_at = datetime.now(UTC)
        await self.projects.save(project)
        try:
            await self.dispatcher.dispatch(project_id)
        except Exception as exc:
            project.status = ProjectStatus.FAILED
            project.updated_at = datetime.now(UTC)
            await self.projects.save(project)
            raise AppError(503, "ANALYSIS_QUEUE_UNAVAILABLE", "Project analysis could not be queued") from exc
        refreshed = await self.projects.get(project_id)
        return ProjectService._response(refreshed or project)

    async def run(self, project_id: str) -> None:
        project = await self.projects.get(project_id)
        if project is None:
            return
        try:
            archive = await self.storage.read(project.object_name)
            result = await asyncio.to_thread(
                analyze_zip,
                project.id,
                archive,
                self.max_python_files,
                self.max_uncompressed_bytes,
            )
            await self.functions.replace_for_project(project.id, result.functions)
            project.python_file_count = result.python_file_count
            project.function_count = len(result.functions)
            project.statement_count = result.statement_count
            project.branch_count = result.branch_count
            project.status = ProjectStatus.WARNING if result.warning_count else ProjectStatus.READY
            project.analyzed_at = datetime.now(UTC)
            project.updated_at = project.analyzed_at
            await self.projects.save(project)
        except Exception:
            project.status = ProjectStatus.FAILED
            project.updated_at = datetime.now(UTC)
            await self.projects.save(project)
            raise

    async def list_functions(self, project_id: str, owner_id: str) -> ProjectFunctionListResponse:
        project = await self.project_service.require_owned(project_id, owner_id)
        if project.status in {ProjectStatus.UPLOADED, ProjectStatus.ANALYZING}:
            raise AppError(409, "ANALYSIS_NOT_READY", "Project analysis has not completed")
        functions = await self.functions.list_for_project(project_id)
        return ProjectFunctionListResponse(
            items=[
                ProjectFunctionResponse.model_validate(item.model_dump(exclude={"source", "analyzed_at"}))
                for item in functions
            ],
            total=len(functions),
        )

    async def get_source(self, project_id: str, function_id: str, owner_id: str) -> FunctionSourceResponse:
        await self.project_service.require_owned(project_id, owner_id)
        function = await self.functions.get(project_id, function_id)
        if function is None:
            raise AppError(404, "FUNCTION_NOT_FOUND", "Analyzed function was not found")
        return FunctionSourceResponse(source=function.source)
