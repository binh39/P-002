from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class UploadStatus(StrEnum):
    PENDING = "pending"
    UPLOADED = "uploaded"


class CreateUploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(default="application/zip", max_length=100)
    size_bytes: int = Field(gt=0)

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, value: str) -> str:
        if "/" in value or "\\" in value or not value.lower().endswith(".zip"):
            raise ValueError("filename must be a plain .zip file name")
        return value

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, value: str) -> str:
        allowed = {"application/zip", "application/x-zip-compressed"}
        if value.lower() not in allowed:
            raise ValueError("only ZIP uploads are supported")
        return value.lower()


class UploadResponse(BaseModel):
    id: str
    filename: str
    object_name: str
    status: UploadStatus
    size_bytes: int
    upload_url: str | None = None
    method: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    expires_at: datetime
    created_at: datetime
