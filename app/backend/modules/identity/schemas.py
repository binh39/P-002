from pydantic import BaseModel

from backend.core.security import UserRole


class CurrentIdentityResponse(BaseModel):
    id: str
    name: str | None = None
    email: str | None = None
    role: UserRole
    workspace_id: str
    permissions: list[str]
