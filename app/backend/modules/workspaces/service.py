from datetime import UTC, datetime

from backend.core.errors import AppError
from backend.core.security import AuthenticatedUser, UserRole

from .repository import WorkspaceRepository
from .schemas import UserProfile, WorkspaceMember, WorkspaceResponse, new_workspace


class WorkspaceService:
    def __init__(self, repository: WorkspaceRepository):
        self.repository = repository

    async def resolve(self, identity: AuthenticatedUser) -> AuthenticatedUser:
        profile = await self.repository.get_profile(identity.uid)
        if profile is None:
            profile = await self._create_legacy_profile(identity)
        workspace = await self.repository.get_workspace(profile.active_workspace_id)
        if workspace is None or not self._is_member(workspace, identity.uid):
            workspace = await self._ensure_personal_workspace(profile)
            profile.active_workspace_id = workspace.id
            profile.updated_at = datetime.now(UTC)
            await self.repository.save_profile(profile)
        return AuthenticatedUser(
            uid=identity.uid,
            email=profile.email or identity.email,
            name=profile.name,
            role=profile.role,
            workspace_id=profile.active_workspace_id,
        )

    async def onboard(self, identity: AuthenticatedUser, role: UserRole, name: str | None) -> AuthenticatedUser:
        profile = await self.repository.get_profile(identity.uid)
        if profile is not None and profile.onboarding_completed:
            if profile.role != role:
                raise AppError(409, "ONBOARDING_ALREADY_COMPLETED", "Account role has already been selected")
        else:
            now = datetime.now(UTC)
            profile = profile or UserProfile(
                id=identity.uid,
                email=identity.email.casefold() if identity.email else None,
                name=(name or identity.name or identity.email or "PromptOpt User").strip(),
                role=role,
                active_workspace_id=identity.workspace_id or identity.uid,
                created_at=now,
                updated_at=now,
            )
            profile.role = role
            profile.name = (name or profile.name).strip()
            profile.onboarding_completed = True
            profile.updated_at = now
            await self.repository.save_profile(profile)
            workspace = await self._ensure_personal_workspace(profile)
            member = next((item for item in workspace.members if item.user_id == profile.id), None)
            if member is not None:
                member.role = role
                member.name = profile.name
            await self.repository.save_workspace(workspace)
        return await self.resolve(identity)

    async def list(self, user_id: str) -> list[WorkspaceResponse]:
        return await self.repository.list_for_member(user_id)

    async def create(self, user: AuthenticatedUser, name: str) -> WorkspaceResponse:
        profile = await self._required_profile(user.uid)
        workspace = new_workspace(profile, name)
        await self.repository.save_workspace(workspace)
        profile.active_workspace_id = workspace.id
        profile.updated_at = datetime.now(UTC)
        await self.repository.save_profile(profile)
        return workspace

    async def switch(self, user_id: str, workspace_id: str) -> WorkspaceResponse:
        profile = await self._required_profile(user_id)
        workspace = await self._required_workspace(workspace_id, user_id)
        profile.active_workspace_id = workspace.id
        profile.updated_at = datetime.now(UTC)
        await self.repository.save_profile(profile)
        return workspace

    async def rename(self, user_id: str, workspace_id: str, name: str) -> WorkspaceResponse:
        workspace = await self._required_workspace(workspace_id, user_id)
        self._require_owner(workspace, user_id)
        workspace.name = name
        workspace.updated_at = datetime.now(UTC)
        return await self.repository.save_workspace(workspace)

    async def add_member(self, user_id: str, workspace_id: str, email: str) -> WorkspaceResponse:
        workspace = await self._required_workspace(workspace_id, user_id)
        self._require_owner(workspace, user_id)
        profile = await self.repository.get_profile_by_email(email)
        if profile is None:
            raise AppError(404, "MEMBER_NOT_FOUND", "No registered account has that email address")
        if not self._is_member(workspace, profile.id):
            workspace.members.append(
                WorkspaceMember(
                    user_id=profile.id,
                    email=profile.email,
                    name=profile.name,
                    role=profile.role,
                    joined_at=datetime.now(UTC),
                )
            )
            workspace.updated_at = datetime.now(UTC)
            await self.repository.save_workspace(workspace)
        return workspace

    async def remove_member(self, user_id: str, workspace_id: str, member_id: str) -> WorkspaceResponse:
        workspace = await self._required_workspace(workspace_id, user_id)
        self._require_owner(workspace, user_id)
        if member_id == workspace.owner_id:
            raise AppError(409, "WORKSPACE_OWNER_REQUIRED", "The workspace owner cannot be removed")
        workspace.members = [member for member in workspace.members if member.user_id != member_id]
        workspace.updated_at = datetime.now(UTC)
        return await self.repository.save_workspace(workspace)

    async def _create_legacy_profile(self, identity: AuthenticatedUser) -> UserProfile:
        now = datetime.now(UTC)
        profile = UserProfile(
            id=identity.uid,
            email=identity.email.casefold() if identity.email else None,
            name=identity.name or identity.email or "PromptOpt User",
            role=identity.role,
            active_workspace_id=identity.workspace_id or identity.uid,
            onboarding_completed=True,
            created_at=now,
            updated_at=now,
        )
        await self.repository.save_profile(profile)
        await self._ensure_personal_workspace(profile)
        return profile

    async def _ensure_personal_workspace(self, profile: UserProfile) -> WorkspaceResponse:
        workspace = await self.repository.get_workspace(profile.active_workspace_id)
        if workspace is None:
            workspace = new_workspace(profile, "Workspace 1", profile.active_workspace_id)
            await self.repository.save_workspace(workspace)
        elif not self._is_member(workspace, profile.id):
            workspace.members.append(
                WorkspaceMember(
                    user_id=profile.id,
                    email=profile.email,
                    name=profile.name,
                    role=profile.role,
                    joined_at=datetime.now(UTC),
                )
            )
            workspace.updated_at = datetime.now(UTC)
            await self.repository.save_workspace(workspace)
        return workspace

    async def _required_profile(self, user_id: str) -> UserProfile:
        profile = await self.repository.get_profile(user_id)
        if profile is None:
            raise AppError(404, "PROFILE_NOT_FOUND", "User profile was not found")
        return profile

    async def _required_workspace(self, workspace_id: str, user_id: str) -> WorkspaceResponse:
        workspace = await self.repository.get_workspace(workspace_id)
        if workspace is None or not self._is_member(workspace, user_id):
            raise AppError(404, "WORKSPACE_NOT_FOUND", "Workspace was not found")
        return workspace

    @staticmethod
    def _is_member(workspace: WorkspaceResponse, user_id: str) -> bool:
        return any(member.user_id == user_id for member in workspace.members)

    @staticmethod
    def _require_owner(workspace: WorkspaceResponse, user_id: str) -> None:
        if workspace.owner_id != user_id:
            raise AppError(403, "WORKSPACE_OWNER_REQUIRED", "Only the workspace owner can change these settings")
