from fastapi import APIRouter, Request, status

from backend.api.dependencies import CurrentUser, RawCurrentUser

from .schemas import (
    AddWorkspaceMemberRequest,
    CreateWorkspaceRequest,
    OnboardingRequest,
    RenameWorkspaceRequest,
    WorkspaceListResponse,
    WorkspaceResponse,
)

router = APIRouter(tags=["workspaces"])


@router.post("/onboarding", status_code=status.HTTP_200_OK)
async def onboard(payload: OnboardingRequest, user: RawCurrentUser, request: Request):
    return await request.app.state.services.workspaces.onboard(user, payload.role, payload.name)


@router.get("/workspaces", response_model=WorkspaceListResponse)
async def list_workspaces(user: CurrentUser, request: Request):
    items = await request.app.state.services.workspaces.list(user.uid)
    return WorkspaceListResponse(items=items, active_workspace_id=user.workspace_id or user.uid)


@router.post("/workspaces", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(payload: CreateWorkspaceRequest, user: CurrentUser, request: Request):
    return await request.app.state.services.workspaces.create(user, payload.name)


@router.post("/workspaces/{workspace_id}/activate", response_model=WorkspaceResponse)
async def activate_workspace(workspace_id: str, user: CurrentUser, request: Request):
    return await request.app.state.services.workspaces.switch(user.uid, workspace_id)


@router.patch("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def rename_workspace(workspace_id: str, payload: RenameWorkspaceRequest, user: CurrentUser, request: Request):
    return await request.app.state.services.workspaces.rename(user.uid, workspace_id, payload.name)


@router.post("/workspaces/{workspace_id}/members", response_model=WorkspaceResponse)
async def add_member(workspace_id: str, payload: AddWorkspaceMemberRequest, user: CurrentUser, request: Request):
    return await request.app.state.services.workspaces.add_member(user.uid, workspace_id, payload.email)


@router.delete("/workspaces/{workspace_id}/members/{member_id}", response_model=WorkspaceResponse)
async def remove_member(workspace_id: str, member_id: str, user: CurrentUser, request: Request):
    return await request.app.state.services.workspaces.remove_member(user.uid, workspace_id, member_id)
