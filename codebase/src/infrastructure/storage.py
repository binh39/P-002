import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from src.core.errors import AppError


@dataclass(frozen=True, slots=True)
class UploadTarget:
    url: str
    method: str
    headers: dict[str, str]


class ObjectStorage(Protocol):
    async def create_upload_target(
        self,
        upload_id: str,
        object_name: str,
        content_type: str,
        expires_at: datetime,
    ) -> UploadTarget: ...

    async def put_local(self, object_name: str, content: bytes) -> None: ...

    async def exists(self, object_name: str) -> bool: ...

    async def size(self, object_name: str) -> int: ...


class LocalObjectStorage:
    def __init__(self, directory: str, api_prefix: str):
        self.root = Path(directory).resolve()
        self.api_prefix = api_prefix
        self.root.mkdir(parents=True, exist_ok=True)

    async def create_upload_target(
        self,
        upload_id: str,
        object_name: str,
        content_type: str,
        expires_at: datetime,
    ) -> UploadTarget:
        del object_name, expires_at
        return UploadTarget(
            url=f"{self.api_prefix}/uploads/{upload_id}/content",
            method="PUT",
            headers={"Content-Type": content_type},
        )

    async def put_local(self, object_name: str, content: bytes) -> None:
        target = (self.root / object_name).resolve()
        if self.root not in target.parents:
            raise AppError(400, "INVALID_OBJECT_NAME", "Upload destination is invalid")
        target.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(target.write_bytes, content)

    async def exists(self, object_name: str) -> bool:
        target = (self.root / object_name).resolve()
        return self.root in target.parents and await asyncio.to_thread(target.is_file)

    async def size(self, object_name: str) -> int:
        target = (self.root / object_name).resolve()
        if self.root not in target.parents or not await asyncio.to_thread(target.is_file):
            raise AppError(404, "UPLOAD_NOT_FOUND", "The source archive was not found")
        return (await asyncio.to_thread(target.stat)).st_size


class GcsObjectStorage:
    def __init__(self, project_id: str, bucket_name: str):
        from google.cloud import storage

        self.client = storage.Client(project=project_id)
        self.bucket = self.client.bucket(bucket_name)

    async def create_upload_target(
        self,
        upload_id: str,
        object_name: str,
        content_type: str,
        expires_at: datetime,
    ) -> UploadTarget:
        del upload_id
        blob = self.bucket.blob(object_name)
        url = await asyncio.to_thread(
            blob.generate_signed_url,
            version="v4",
            expiration=expires_at,
            method="PUT",
            content_type=content_type,
        )
        return UploadTarget(url=url, method="PUT", headers={"Content-Type": content_type})

    async def put_local(self, object_name: str, content: bytes) -> None:
        del object_name, content
        raise AppError(404, "LOCAL_UPLOAD_DISABLED", "Upload content directly to the signed URL")

    async def exists(self, object_name: str) -> bool:
        return await asyncio.to_thread(self.bucket.blob(object_name).exists, self.client)

    async def size(self, object_name: str) -> int:
        blob = self.bucket.blob(object_name)
        await asyncio.to_thread(blob.reload, client=self.client)
        return int(blob.size or 0)
