from typing import Protocol

from backend.modules.projects.schemas import ProjectRecord


class ProjectRepository(Protocol):
    async def create(self, project: ProjectRecord) -> ProjectRecord: ...

    async def get(self, project_id: str) -> ProjectRecord | None: ...

    async def list_for_owner(self, owner_id: str) -> list[ProjectRecord]: ...

    async def save(self, project: ProjectRecord) -> ProjectRecord: ...


class InMemoryProjectRepository:
    def __init__(self):
        self.items: dict[str, ProjectRecord] = {}

    async def create(self, project: ProjectRecord) -> ProjectRecord:
        self.items[project.id] = project
        return project

    async def get(self, project_id: str) -> ProjectRecord | None:
        return self.items.get(project_id)

    async def list_for_owner(self, owner_id: str) -> list[ProjectRecord]:
        projects = [project for project in self.items.values() if project.owner_id == owner_id]
        return sorted(projects, key=lambda project: project.created_at, reverse=True)

    async def save(self, project: ProjectRecord) -> ProjectRecord:
        self.items[project.id] = project
        return project


class FirestoreProjectRepository:
    def __init__(self, client):
        self.collection = client.collection("projects")

    async def create(self, project: ProjectRecord) -> ProjectRecord:
        await self.collection.document(project.id).create(project.model_dump(mode="python"))
        return project

    async def get(self, project_id: str) -> ProjectRecord | None:
        snapshot = await self.collection.document(project_id).get()
        return ProjectRecord.model_validate(snapshot.to_dict()) if snapshot.exists else None

    async def list_for_owner(self, owner_id: str) -> list[ProjectRecord]:
        query = self.collection.where("owner_id", "==", owner_id)
        projects = [ProjectRecord.model_validate(snapshot.to_dict()) async for snapshot in query.stream()]
        return sorted(projects, key=lambda project: project.created_at, reverse=True)

    async def save(self, project: ProjectRecord) -> ProjectRecord:
        await self.collection.document(project.id).set(project.model_dump(mode="python"))
        return project
