from fastapi import APIRouter

from backend.api.dependencies import CurrentUser

from .schemas import CurrentIdentityResponse

router = APIRouter(tags=["identity"])


@router.get("/me", response_model=CurrentIdentityResponse)
async def get_current_identity(user: CurrentUser):
    return CurrentIdentityResponse(
        id=user.uid,
        name=user.name,
        email=user.email,
        role=user.role,
        workspace_id=user.workspace_id or user.uid,
        permissions=list(user.permissions),
    )
