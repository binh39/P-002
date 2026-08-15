from typing import Protocol

from backend.modules.analysis.schemas import ProjectFunctionRecord


class FunctionRepository(Protocol):
    async def replace_for_project(self, project_id: str, functions: list[ProjectFunctionRecord]) -> None: ...

    async def list_for_project(self, project_id: str) -> list[ProjectFunctionRecord]: ...

    async def get(self, project_id: str, function_id: str) -> ProjectFunctionRecord | None: ...


class InMemoryFunctionRepository:
    def __init__(self):
        self.items: dict[str, dict[str, ProjectFunctionRecord]] = {}

    async def replace_for_project(self, project_id: str, functions: list[ProjectFunctionRecord]) -> None:
        self.items[project_id] = {item.id: item for item in functions}

    async def list_for_project(self, project_id: str) -> list[ProjectFunctionRecord]:
        return sorted(
            self.items.get(project_id, {}).values(),
            key=lambda item: (item.file, item.start_line, item.qualified_name),
        )

    async def get(self, project_id: str, function_id: str) -> ProjectFunctionRecord | None:
        return self.items.get(project_id, {}).get(function_id)


class FirestoreFunctionRepository:
    def __init__(self, client):
        self.client = client

    def _collection(self, project_id: str):
        return self.client.collection("projects").document(project_id).collection("functions")

    async def replace_for_project(self, project_id: str, functions: list[ProjectFunctionRecord]) -> None:
        collection = self._collection(project_id)
        existing = [snapshot async for snapshot in collection.stream()]
        operations = [(snapshot.reference, None) for snapshot in existing]
        operations.extend((collection.document(item.id), item.model_dump(mode="python")) for item in functions)
        for offset in range(0, len(operations), 400):
            batch = self.client.batch()
            for reference, payload in operations[offset : offset + 400]:
                if payload is None:
                    batch.delete(reference)
                else:
                    batch.set(reference, payload)
            await batch.commit()

    async def list_for_project(self, project_id: str) -> list[ProjectFunctionRecord]:
        items = [
            ProjectFunctionRecord.model_validate(snapshot.to_dict())
            async for snapshot in self._collection(project_id).stream()
        ]
        return sorted(items, key=lambda item: (item.file, item.start_line, item.qualified_name))

    async def get(self, project_id: str, function_id: str) -> ProjectFunctionRecord | None:
        snapshot = await self._collection(project_id).document(function_id).get()
        return ProjectFunctionRecord.model_validate(snapshot.to_dict()) if snapshot.exists else None
