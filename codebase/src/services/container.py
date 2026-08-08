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
from src.modules.experiments.cloud_optimizer import CloudRunJobGepaOptimizer
from src.modules.experiments.dispatcher import (
    CloudTasksComparisonDispatcher,
    CloudTasksOptimizationDispatcher,
    InlineComparisonDispatcher,
    InlineOptimizationDispatcher,
)
from src.modules.experiments.repository import FirestoreExperimentRepository, InMemoryExperimentRepository
from src.modules.experiments.service import ExperimentService
from src.modules.projects.repository import (
    FirestoreProjectRepository,
    InMemoryProjectRepository,
    ProjectRepository,
)
from src.modules.projects.samples import SampleProjectCatalog
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
    experiments: ExperimentService


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

    experiment_repository = (
        FirestoreExperimentRepository(firestore)
        if settings.repository_backend == "firestore"
        else InMemoryExperimentRepository()
    )

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
    samples = SampleProjectCatalog(
        settings.sample_repos_dir,
        settings.max_analysis_python_files,
        settings.max_analysis_uncompressed_bytes,
    )
    projects = ProjectService(project_repository, uploads, samples)
    analysis = AnalysisService(
        project_repository,
        function_repository,
        projects,
        storage,
        settings.max_analysis_python_files,
        settings.max_analysis_uncompressed_bytes,
        samples,
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
    cloud_optimizer = None
    if settings.optimization_execution_backend == "cloud_run_job":
        from google.cloud import run_v2

        cloud_optimizer = CloudRunJobGepaOptimizer(
            client=run_v2.JobsClient(),
            storage=storage,
            bucket=settings.gcs_bucket,
            job_name=(
                f"projects/{settings.gcp_project_id}/locations/{settings.cloud_tasks_location}/jobs/"
                f"{settings.cloud_run_gepa_job}"
            ),
            timeout_seconds=settings.cloud_run_gepa_timeout_seconds,
        )
    experiments = ExperimentService(
        experiment_repository,
        projects,
        function_repository,
        storage,
        cloud_optimizer=cloud_optimizer,
        samples=samples,
    )
    if settings.experiment_dispatcher == "cloud_tasks":
        experiments.set_optimization_dispatcher(
            CloudTasksOptimizationDispatcher(
                settings.gcp_project_id,
                settings.cloud_tasks_location,
                settings.experiment_cloud_tasks_queue,
                settings.experiment_worker_url,
                settings.experiment_task_audience,
                settings.gcp_service_account_email,
            )
        )
        experiments.set_comparison_dispatcher(
            CloudTasksComparisonDispatcher(
                settings.gcp_project_id,
                settings.cloud_tasks_location,
                settings.experiment_cloud_tasks_queue,
                settings.experiment_worker_url,
                settings.experiment_task_audience,
                settings.gcp_service_account_email,
            )
        )
    else:
        experiments.set_optimization_dispatcher(InlineOptimizationDispatcher(experiments.execute_optimization))
        experiments.set_comparison_dispatcher(InlineComparisonDispatcher(experiments.execute_comparison))
    return ServiceContainer(
        token_verifier=token_verifier,
        internal_token_verifier=internal_token_verifier,
        uploads=uploads,
        projects=projects,
        analysis=analysis,
        experiments=experiments,
    )
