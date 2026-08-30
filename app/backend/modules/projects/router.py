from fastapi import APIRouter, Request, status

from backend.api.dependencies import CurrentUser, EngineerUser
from backend.modules.projects.schemas import (
    CreateProjectRequest,
    ProjectListResponse,
    ProjectResponse,
    ProjectSettingsPatch,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(payload: CreateProjectRequest, user: EngineerUser, request: Request):
    return await request.app.state.services.projects.create(user.uid, payload, user.workspace_id)


@router.get("", response_model=ProjectListResponse)
async def list_projects(user: CurrentUser, request: Request):
    return await request.app.state.services.projects.list(user.uid, user.workspace_id)


@router.get("/samples", response_model=ProjectListResponse)
async def list_sample_projects(user: CurrentUser, request: Request):
    return await request.app.state.services.projects.list_samples(user.uid)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, user: CurrentUser, request: Request):
    return await request.app.state.services.projects.get(project_id, user.uid, user.workspace_id)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: str, user: EngineerUser, request: Request):
    await request.app.state.services.projects.delete(project_id, user.uid)


@router.post("/{project_id}/prepare-runtime", response_model=ProjectResponse, status_code=status.HTTP_202_ACCEPTED)
async def prepare_project_runtime(project_id: str, user: EngineerUser, request: Request):
    return await request.app.state.services.projects.prepare_runtime(project_id, user.uid)


@router.patch("/{project_id}/settings", response_model=ProjectResponse)
async def update_project_settings(
    project_id: str,
    payload: ProjectSettingsPatch,
    user: EngineerUser,
    request: Request,
):
    return await request.app.state.services.projects.update_settings(project_id, user.uid, payload)
