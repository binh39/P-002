from datetime import UTC, datetime, timedelta
from uuid import uuid4

from backend.core.errors import AppError
from backend.infrastructure.storage import ObjectStorage
from backend.modules.uploads.repository import UploadRecord, UploadRepository
from backend.modules.uploads.schemas import (
    CreateUploadRequest,
    UploadProjectSettings,
    UploadResponse,
    UploadRuntimeSettings,
    UploadStatus,
)


class UploadService:
    def __init__(
        self,
        repository: UploadRepository,
        storage: ObjectStorage,
        max_upload_bytes: int,
        signed_url_ttl_seconds: int,
    ):
        self.repository = repository
        self.storage = storage
        self.max_upload_bytes = max_upload_bytes
        self.signed_url_ttl_seconds = signed_url_ttl_seconds

    async def create(self, owner_id: str, request: CreateUploadRequest) -> UploadResponse:
        if request.size_bytes > self.max_upload_bytes:
            raise AppError(
                413,
                "UPLOAD_TOO_LARGE",
                f"ZIP archive exceeds the {self.max_upload_bytes} byte limit",
            )
        now = datetime.now(UTC)
        upload_id = str(uuid4())
        object_name = f"users/{owner_id}/uploads/{upload_id}/{request.filename}"
        record = UploadRecord(
            id=upload_id,
            owner_id=owner_id,
            filename=request.filename,
            object_name=object_name,
            content_type=request.content_type,
            size_bytes=request.size_bytes,
            status=UploadStatus.PENDING,
            expires_at=now + timedelta(seconds=self.signed_url_ttl_seconds),
            created_at=now,
            requested_python_version=request.settings.runtime.python_version,
        )
        await self.repository.create(record)
        target = await self.storage.create_upload_target(
            record.id,
            record.object_name,
            record.content_type,
            record.expires_at,
        )
        return self._response(record, target.url, target.method, target.headers)

    async def put_local(self, upload_id: str, owner_id: str, content: bytes) -> UploadRecord:
        record = await self.require_owned(upload_id, owner_id)
        if datetime.now(UTC) > record.expires_at:
            raise AppError(410, "UPLOAD_EXPIRED", "The upload URL has expired")
        if len(content) != record.size_bytes:
            raise AppError(400, "UPLOAD_SIZE_MISMATCH", "Uploaded content size does not match the request")
        await self.storage.put_local(record.object_name, content)
        record.status = UploadStatus.UPLOADED
        return await self.repository.save(record)

    async def complete(self, upload_id: str, owner_id: str) -> UploadResponse:
        record = await self.require_owned(upload_id, owner_id)
        if not await self.storage.exists(record.object_name):
            raise AppError(409, "UPLOAD_NOT_FOUND", "The source archive has not been uploaded yet")
        if await self.storage.size(record.object_name) != record.size_bytes:
            raise AppError(409, "UPLOAD_SIZE_MISMATCH", "Uploaded content size does not match the request")
        record.status = UploadStatus.UPLOADED
        await self.repository.save(record)
        return self._response(record)

    async def require_ready(self, upload_id: str, owner_id: str) -> UploadRecord:
        record = await self.require_owned(upload_id, owner_id)
        if record.status != UploadStatus.UPLOADED:
            raise AppError(409, "UPLOAD_NOT_READY", "Complete the ZIP upload before creating a project")
        return record

    async def require_owned(self, upload_id: str, owner_id: str) -> UploadRecord:
        record = await self.repository.get(upload_id)
        if record is None or record.owner_id != owner_id:
            raise AppError(404, "UPLOAD_NOT_FOUND", "Upload was not found")
        return record

    async def delete(self, upload_id: str, owner_id: str) -> None:
        record = await self.require_owned(upload_id, owner_id)
        await self.storage.delete(record.object_name)
        await self.repository.delete(record.id)

    @staticmethod
    def _response(
        record: UploadRecord,
        upload_url: str | None = None,
        method: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> UploadResponse:
        return UploadResponse(
            id=record.id,
            filename=record.filename,
            object_name=record.object_name,
            status=record.status,
            size_bytes=record.size_bytes,
            settings=UploadProjectSettings(
                runtime=UploadRuntimeSettings(python_version=record.requested_python_version)
            ),
            upload_url=upload_url,
            method=method,
            headers=headers or {},
            expires_at=record.expires_at,
            created_at=record.created_at,
        )
