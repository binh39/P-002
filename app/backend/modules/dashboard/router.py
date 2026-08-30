from fastapi import APIRouter, Request

from backend.api.dependencies import CurrentUser

from .schemas import DashboardResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(user: CurrentUser, request: Request):
    include_legacy = await request.app.state.services.workspaces.is_personal_workspace(user.uid, user.workspace_id)
    return await request.app.state.services.dashboard.snapshot(user.uid, user.workspace_id, include_legacy)
