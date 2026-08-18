from dataclasses import dataclass

from backend.config import Settings
from backend.core.security import (
    DevelopmentTokenVerifier,
    FirebaseTokenVerifier,
    GoogleOidcTokenVerifier,
    TokenVerifier,
)
from backend.infrastructure.storage import GcsObjectStorage, LocalObjectStorage
from backend.modules.analysis.dispatcher import CloudTasksAnalysisDispatcher, InlineAnalysisDispatcher
from backend.modules.analysis.repository import (
    FirestoreFunctionRepository,
    FunctionRepository,
    InMemoryFunctionRepository,
)
from backend.modules.analysis.service import AnalysisService
from backend.modules.dashboard.service import DashboardService
from backend.modules.experiments.cloud_optimizer import CloudRunJobGepaOptimizer
from backend.modules.experiments.dispatcher import (
    CloudTasksComparisonDispatcher,
    CloudTasksOptimizationDispatcher,
    InlineComparisonDispatcher,
    InlineOptimizationDispatcher,
)
from backend.modules.experiments.repository import FirestoreExperimentRepository, InMemoryExperimentRepository
from backend.modules.experiments.service import ExperimentService
from backend.modules.projects.repository import (
    FirestoreProjectRepository,
    InMemoryProjectRepository,
    ProjectRepository,
)
from backend.modules.projects.runtime import CloudRunRuntimePreparer, RuntimePreparationService
from backend.modules.projects.samples import SampleProjectCatalog
from backend.modules.projects.service import ProjectService
from backend.modules.providers.service import (
    InMemoryProviderCredentialStore,
    ProviderCredentialService,
    SecretManagerProviderCredentialStore,
)
from backend.modules.uploads.repository import (
    FirestoreUploadRepository,
    InMemoryUploadRepository,
    UploadRepository,
)
from backend.modules.uploads.service import UploadService


@dataclass(slots=True)
class ServiceContainer:
    token_verifier: TokenVerifier
    internal_token_verifier: GoogleOidcTokenVerifier | None
    uploads: UploadService
    projects: ProjectService
    analysis: AnalysisService
    experiments: ExperimentService
    dashboard: DashboardService
    provider_credentials: ProviderCredentialService


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
    credential_store = (
        SecretManagerProviderCredentialStore(settings.gcp_project_id, settings.provider_secret_prefix)
        if settings.app_env == "production"
        else InMemoryProviderCredentialStore()
    )
    provider_credentials = ProviderCredentialService(credential_store)

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
    runtime_runner = None
    if settings.runtime_execution_backend == "cloud_run_job":
        from google.cloud import run_v2

        runtime_runner = CloudRunRuntimePreparer(
            client=run_v2.JobsClient(),
            storage=storage,
            bucket=settings.gcs_bucket,
            job_name=(
                f"projects/{settings.gcp_project_id}/locations/{settings.cloud_tasks_location}/jobs/"
                f"{settings.cloud_run_runtime_job}"
            ),
            timeout_seconds=settings.cloud_run_runtime_timeout_seconds,
        )
    runtime = RuntimePreparationService(project_repository, runtime_runner)
    projects.set_runtime_service(runtime)
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
        from google.cloud import logging_v2, run_v2

        cloud_optimizer = CloudRunJobGepaOptimizer(
            client=run_v2.JobsClient(),
            storage=storage,
            bucket=settings.gcs_bucket,
            job_name=(
                f"projects/{settings.gcp_project_id}/locations/{settings.cloud_tasks_location}/jobs/"
                f"{settings.cloud_run_gepa_job}"
            ),
            timeout_seconds=settings.cloud_run_gepa_timeout_seconds,
            logging_client=logging_v2.Client(project=settings.gcp_project_id),
            executions_client=run_v2.ExecutionsClient(),
        )
    experiments = ExperimentService(
        experiment_repository,
        projects,
        function_repository,
        storage,
        cloud_optimizer=cloud_optimizer,
        samples=samples,
        admin_vertexai_project=settings.admin_vertexai_project,
        provider_credentials=provider_credentials,
    )
    dashboard = DashboardService(experiment_repository)
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
        dashboard=dashboard,
        provider_credentials=provider_credentials,
    )
