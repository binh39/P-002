from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Protocol

from backend.modules.uploads.schemas import UploadStatus


@dataclass(slots=True)
class UploadRecord:
    id: str
    owner_id: str
    filename: str
    object_name: str
    content_type: str
    size_bytes: int
    status: UploadStatus
    expires_at: datetime
    created_at: datetime
    requested_python_version: str = "3.12"


class UploadRepository(Protocol):
    async def create(self, upload: UploadRecord) -> UploadRecord: ...

    async def get(self, upload_id: str) -> UploadRecord | None: ...

    async def save(self, upload: UploadRecord) -> UploadRecord: ...

    async def delete(self, upload_id: str) -> None: ...


class InMemoryUploadRepository:
    def __init__(self):
        self.items: dict[str, UploadRecord] = {}

    async def create(self, upload: UploadRecord) -> UploadRecord:
        self.items[upload.id] = upload
        return upload

    async def get(self, upload_id: str) -> UploadRecord | None:
        return self.items.get(upload_id)

    async def save(self, upload: UploadRecord) -> UploadRecord:
        self.items[upload.id] = upload
        return upload

    async def delete(self, upload_id: str) -> None:
        self.items.pop(upload_id, None)


class FirestoreUploadRepository:
    def __init__(self, client):
        self.collection = client.collection("uploads")

    async def create(self, upload: UploadRecord) -> UploadRecord:
        await self.collection.document(upload.id).create(self._serialize(upload))
        return upload

    async def get(self, upload_id: str) -> UploadRecord | None:
        snapshot = await self.collection.document(upload_id).get()
        if not snapshot.exists:
            return None
        return self._deserialize(snapshot.to_dict())

    async def save(self, upload: UploadRecord) -> UploadRecord:
        await self.collection.document(upload.id).set(self._serialize(upload))
        return upload

    async def delete(self, upload_id: str) -> None:
        await self.collection.document(upload_id).delete()

    @staticmethod
    def _serialize(upload: UploadRecord) -> dict:
        payload = asdict(upload)
        payload["status"] = upload.status.value
        return payload

    @staticmethod
    def _deserialize(payload: dict) -> UploadRecord:
        payload["status"] = UploadStatus(payload["status"])
        payload.setdefault("requested_python_version", "3.12")
        return UploadRecord(**payload)
