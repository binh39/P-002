from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.core.security import UserRole


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WorkspaceMember(StrictModel):
    user_id: str
    email: str | None = None
    name: str
    role: UserRole
    joined_at: datetime


class WorkspaceResponse(StrictModel):
    id: str
    name: str
    owner_id: str
    members: list[WorkspaceMember]
    created_at: datetime
    updated_at: datetime


class UserProfile(StrictModel):
    id: str
    email: str | None = None
    name: str
    role: UserRole
    active_workspace_id: str
    onboarding_completed: bool = False
    created_at: datetime
    updated_at: datetime


class OnboardingRequest(StrictModel):
    role: UserRole
    name: str | None = Field(default=None, min_length=2, max_length=120)


class CreateWorkspaceRequest(StrictModel):
    name: str = Field(default="New Workspace", min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Workspace name cannot be blank")
        return value


class RenameWorkspaceRequest(CreateWorkspaceRequest):
    pass


class AddWorkspaceMemberRequest(StrictModel):
    email: str = Field(min_length=3, max_length=320)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().casefold()


class WorkspaceListResponse(StrictModel):
    items: list[WorkspaceResponse]
    active_workspace_id: str


def new_workspace(owner: UserProfile, name: str, workspace_id: str | None = None) -> WorkspaceResponse:
    now = datetime.now(UTC)
    return WorkspaceResponse(
        id=workspace_id or str(uuid4()),
        name=name,
        owner_id=owner.id,
        members=[
            WorkspaceMember(
                user_id=owner.id,
                email=owner.email,
                name=owner.name,
                role=owner.role,
                joined_at=now,
            )
        ],
        created_at=now,
        updated_at=now,
    )
