from typing import Protocol

from .schemas import UserProfile, WorkspaceResponse


class WorkspaceRepository(Protocol):
    async def get_profile(self, user_id: str) -> UserProfile | None: ...
    async def get_profile_by_email(self, email: str) -> UserProfile | None: ...
    async def save_profile(self, profile: UserProfile) -> UserProfile: ...
    async def get_workspace(self, workspace_id: str) -> WorkspaceResponse | None: ...
    async def list_for_member(self, user_id: str) -> list[WorkspaceResponse]: ...
    async def save_workspace(self, workspace: WorkspaceResponse) -> WorkspaceResponse: ...


class InMemoryWorkspaceRepository:
    def __init__(self):
        self.profiles: dict[str, UserProfile] = {}
        self.workspaces: dict[str, WorkspaceResponse] = {}

    async def get_profile(self, user_id):
        return self.profiles.get(user_id)

    async def get_profile_by_email(self, email):
        normalized = email.casefold()
        return next((p for p in self.profiles.values() if p.email and p.email.casefold() == normalized), None)

    async def save_profile(self, profile):
        self.profiles[profile.id] = profile
        return profile

    async def get_workspace(self, workspace_id):
        return self.workspaces.get(workspace_id)

    async def list_for_member(self, user_id):
        items = [w for w in self.workspaces.values() if any(m.user_id == user_id for m in w.members)]
        return sorted(items, key=lambda item: item.created_at)

    async def save_workspace(self, workspace):
        self.workspaces[workspace.id] = workspace
        return workspace


class FirestoreWorkspaceRepository:
    def __init__(self, client):
        self.profiles = client.collection("user_profiles")
        self.workspaces = client.collection("workspaces")

    async def get_profile(self, user_id):
        snapshot = await self.profiles.document(user_id).get()
        return UserProfile.model_validate(snapshot.to_dict()) if snapshot.exists else None

    async def get_profile_by_email(self, email):
        query = self.profiles.where("email", "==", email.casefold()).limit(1)
        async for snapshot in query.stream():
            return UserProfile.model_validate(snapshot.to_dict())
        return None

    async def save_profile(self, profile):
        await self.profiles.document(profile.id).set(profile.model_dump(mode="python"))
        return profile

    async def get_workspace(self, workspace_id):
        snapshot = await self.workspaces.document(workspace_id).get()
        if not snapshot.exists:
            return None
        data = snapshot.to_dict()
        data.pop("member_ids", None)
        return WorkspaceResponse.model_validate(data)

    async def list_for_member(self, user_id):
        query = self.workspaces.where("member_ids", "array_contains", user_id)
        items = []
        async for snapshot in query.stream():
            data = snapshot.to_dict()
            data.pop("member_ids", None)
            items.append(WorkspaceResponse.model_validate(data))
        return sorted(items, key=lambda item: item.created_at)

    async def save_workspace(self, workspace):
        data = workspace.model_dump(mode="python")
        data["member_ids"] = [member.user_id for member in workspace.members]
        await self.workspaces.document(workspace.id).set(data)
        return workspace
