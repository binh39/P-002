from dataclasses import dataclass

from src.config import Settings
from src.core.security import DevelopmentTokenVerifier, FirebaseTokenVerifier, TokenVerifier
from src.infrastructure.storage import GcsObjectStorage, LocalObjectStorage
from src.modules.projects.repository import (
    FirestoreProjectRepository,
    InMemoryProjectRepository,
    ProjectRepository,
)
from src.modules.projects.service import ProjectService
from src.modules.uploads.repository import (
    FirestoreUploadRepository,
    InMemoryUploadRepository,
    UploadRepository,
)
from src.modules.uploads.service import UploadService


@dataclass(slots=True)
class ServiceContainer:
    token_verifier: TokenVerifier
    uploads: UploadService
    projects: ProjectService


def build_services(settings: Settings) -> ServiceContainer:
    token_verifier: TokenVerifier
    if settings.auth_mode == "firebase":
        token_verifier = FirebaseTokenVerifier(settings.gcp_project_id)
    else:
        token_verifier = DevelopmentTokenVerifier()

    upload_repository: UploadRepository
    project_repository: ProjectRepository
    if settings.repository_backend == "firestore":
        from google.cloud.firestore_v1.async_client import AsyncClient

        firestore = AsyncClient(project=settings.gcp_project_id)
        upload_repository = FirestoreUploadRepository(firestore)
        project_repository = FirestoreProjectRepository(firestore)
    else:
        upload_repository = InMemoryUploadRepository()
        project_repository = InMemoryProjectRepository()

    if settings.storage_backend == "gcs":
        storage = GcsObjectStorage(settings.gcp_project_id, settings.gcs_bucket)
    else:
        storage = LocalObjectStorage(settings.local_upload_dir, settings.api_prefix)

    uploads = UploadService(
        repository=upload_repository,
        storage=storage,
        max_upload_bytes=settings.max_upload_bytes,
        signed_url_ttl_seconds=settings.signed_url_ttl_seconds,
    )
    return ServiceContainer(
        token_verifier=token_verifier,
        uploads=uploads,
        projects=ProjectService(project_repository, uploads),
    )
