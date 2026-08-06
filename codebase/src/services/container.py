from dataclasses import dataclass

from src.config import Settings
from src.core.security import (
    DevelopmentTokenVerifier,
    FirebaseTokenVerifier,
    GoogleOidcTokenVerifier,
    TokenVerifier,
)
from src.infrastructure.storage import GcsObjectStorage, LocalObjectStorage
from src.modules.analysis.dispatcher import CloudTasksAnalysisDispatcher, InlineAnalysisDispatcher
from src.modules.analysis.repository import (
    FirestoreFunctionRepository,
    FunctionRepository,
    InMemoryFunctionRepository,
)
from src.modules.analysis.service import AnalysisService
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
    internal_token_verifier: GoogleOidcTokenVerifier | None
    uploads: UploadService
    projects: ProjectService
    analysis: AnalysisService


def build_services(settings: Settings) -> ServiceContainer:
    token_verifier: TokenVerifier
    if settings.auth_mode == "firebase":
        token_verifier = FirebaseTokenVerifier(settings.gcp_project_id)
    else:
        token_verifier = DevelopmentTokenVerifier()

    upload_repository: UploadRepository
    project_repository: ProjectRepository
    function_repository: FunctionRepository
    if settings.repository_backend == "firestore":
        from google.cloud.firestore_v1.async_client import AsyncClient

        firestore = AsyncClient(project=settings.gcp_project_id)
        upload_repository = FirestoreUploadRepository(firestore)
        project_repository = FirestoreProjectRepository(firestore)
        function_repository = FirestoreFunctionRepository(firestore)
    else:
        upload_repository = InMemoryUploadRepository()
        project_repository = InMemoryProjectRepository()
        function_repository = InMemoryFunctionRepository()

    if settings.storage_backend == "gcs":
        storage = GcsObjectStorage(
            settings.gcp_project_id,
            settings.gcs_bucket,
            settings.gcp_service_account_email,
        )
    else:
        storage = LocalObjectStorage(settings.local_upload_dir, settings.api_prefix)

    uploads = UploadService(
        repository=upload_repository,
        storage=storage,
        max_upload_bytes=settings.max_upload_bytes,
        signed_url_ttl_seconds=settings.signed_url_ttl_seconds,
    )
    projects = ProjectService(project_repository, uploads)
    analysis = AnalysisService(
        project_repository,
        function_repository,
        projects,
        storage,
        settings.max_analysis_python_files,
        settings.max_analysis_uncompressed_bytes,
    )
    internal_token_verifier = None
    if settings.analysis_dispatcher == "cloud_tasks":
        dispatcher = CloudTasksAnalysisDispatcher(
            settings.gcp_project_id,
            settings.cloud_tasks_location,
            settings.cloud_tasks_queue,
            settings.analysis_worker_url,
            settings.analysis_task_audience,
            settings.gcp_service_account_email,
        )
        internal_token_verifier = GoogleOidcTokenVerifier(
            settings.analysis_task_audience,
            settings.gcp_service_account_email,
        )
    else:
        dispatcher = InlineAnalysisDispatcher(analysis.run)
    analysis.set_dispatcher(dispatcher)
    return ServiceContainer(
        token_verifier=token_verifier,
        internal_token_verifier=internal_token_verifier,
        uploads=uploads,
        projects=projects,
        analysis=analysis,
    )
