from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Protocol

from src.modules.uploads.schemas import UploadStatus


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


class UploadRepository(Protocol):
    async def create(self, upload: UploadRecord) -> UploadRecord: ...

    async def get(self, upload_id: str) -> UploadRecord | None: ...

    async def save(self, upload: UploadRecord) -> UploadRecord: ...


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

    @staticmethod
    def _serialize(upload: UploadRecord) -> dict:
        payload = asdict(upload)
        payload["status"] = upload.status.value
        return payload

    @staticmethod
    def _deserialize(payload: dict) -> UploadRecord:
        payload["status"] = UploadStatus(payload["status"])
        return UploadRecord(**payload)
