import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from backend.core.errors import AppError


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

    async def read(self, object_name: str) -> bytes: ...

    async def write(self, object_name: str, content: bytes, content_type: str) -> None: ...

    async def generation(self, object_name: str) -> str | None: ...

    async def delete(self, object_name: str) -> None: ...


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

    async def read(self, object_name: str) -> bytes:
        target = (self.root / object_name).resolve()
        if self.root not in target.parents or not await asyncio.to_thread(target.is_file):
            raise AppError(404, "UPLOAD_NOT_FOUND", "The source archive was not found")
        return await asyncio.to_thread(target.read_bytes)

    async def write(self, object_name: str, content: bytes, content_type: str) -> None:
        del content_type
        await self.put_local(object_name, content)

    async def generation(self, object_name: str) -> str | None:
        del object_name
        return None

    async def delete(self, object_name: str) -> None:
        target = (self.root / object_name).resolve()
        if self.root not in target.parents:
            raise AppError(400, "INVALID_OBJECT_NAME", "Upload destination is invalid")
        if await asyncio.to_thread(target.is_file):
            await asyncio.to_thread(target.unlink)


class GcsObjectStorage:
    def __init__(self, project_id: str, bucket_name: str, service_account_email: str):
        import google.auth
        from google.cloud import storage

        self.credentials, _ = google.auth.default()
        self.client = storage.Client(project=project_id, credentials=self.credentials)
        self.bucket = self.client.bucket(bucket_name)
        self.service_account_email = service_account_email

    def _signed_put_url(self, object_name: str, content_type: str, expires_at: datetime) -> str:
        from google.auth.transport.requests import Request

        if not self.credentials.valid:
            self.credentials.refresh(Request())
        return self.bucket.blob(object_name).generate_signed_url(
            version="v4",
            expiration=expires_at,
            method="PUT",
            content_type=content_type,
            service_account_email=self.service_account_email,
            access_token=self.credentials.token,
        )

    async def create_upload_target(
        self,
        upload_id: str,
        object_name: str,
        content_type: str,
        expires_at: datetime,
    ) -> UploadTarget:
        del upload_id
        url = await asyncio.to_thread(self._signed_put_url, object_name, content_type, expires_at)
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

    async def read(self, object_name: str) -> bytes:
        return await asyncio.to_thread(self.bucket.blob(object_name).download_as_bytes)

    async def write(self, object_name: str, content: bytes, content_type: str) -> None:
        blob = self.bucket.blob(object_name)
        await asyncio.to_thread(blob.upload_from_string, content, content_type=content_type)

    async def generation(self, object_name: str) -> str | None:
        blob = self.bucket.blob(object_name)
        await asyncio.to_thread(blob.reload, client=self.client)
        return str(blob.generation) if blob.generation is not None else None

    async def delete(self, object_name: str) -> None:
        blob = self.bucket.blob(object_name)
        if await asyncio.to_thread(blob.exists, self.client):
            await asyncio.to_thread(blob.delete)
