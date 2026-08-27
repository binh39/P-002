from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.modules.projects.schemas import MINIMUM_RUNTIME_PROTOCOL_VERSION

APP_DIRECTORY = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Keep configuration stable when uvicorn/pytest is launched from the
        # repository root, an IDE, or the app directory.
        env_file=APP_DIRECTORY / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "PromptOpt API"
    app_env: Literal["development", "production", "test"] = "development"
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_host: str = "0.0.0.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: str = "http://localhost:5173,https://project-7df9f963-9fe0-4b76-b3d.web.app,https://c3-app-002.io.vn"
    api_prefix: str = "/api/v1"

    # Authentication and Google Cloud
    auth_mode: Literal["disabled", "firebase"] = "disabled"
    repository_backend: Literal["memory", "firestore"] = "memory"
    storage_backend: Literal["local", "gcs"] = "local"
    analysis_dispatcher: Literal["inline", "cloud_tasks"] = "inline"
    gcp_project_id: str = "project-7df9f963-9fe0-4b76-b3d"
    admin_vertexai_project: str = "project-a2f7084e-90ac-4bfc-84b"
    gcp_service_account_email: str = ""
    provider_secret_prefix: str = "promptopt-provider"
    gcs_bucket: str = ""
    cloud_tasks_location: str = "asia-southeast1"
    cloud_tasks_queue: str = "promptopt-analysis"
    analysis_worker_url: str = ""
    analysis_task_audience: str = ""
    experiment_dispatcher: Literal["inline", "cloud_tasks"] = "inline"
    experiment_cloud_tasks_queue: str = "promptopt-baseline"
    experiment_worker_url: str = ""
    experiment_task_audience: str = ""
    optimize_model: str = ""
    optimize_model_allowlist: str = "vertex_ai/gemini-3.1-pro-preview"
    gepa_max_metric_calls: int = Field(default=30, ge=3, le=1000)
    optimization_execution_backend: Literal["inline", "cloud_run_job"] = "inline"
    cloud_run_gepa_job: str = "promptopt-gepa-runner"
    cloud_run_gepa_timeout_seconds: int = Field(default=86400, ge=300, le=86400)
    cloud_run_test_generation_job: str = "promptopt-gepa-runner"
    cloud_run_test_generation_timeout_seconds: int = Field(default=7200, ge=300, le=86400)
    runtime_execution_backend: Literal["disabled", "cloud_run_job"] = "disabled"
    cloud_run_runtime_job: str = "promptopt-runtime-preparer"
    cloud_run_runtime_job_py310: str = ""
    cloud_run_runtime_job_py311: str = ""
    cloud_run_runtime_job_py312: str = ""
    cloud_run_runtime_job_py313: str = ""
    cloud_run_runtime_factory_job: str = "promptopt-runtime-image-factory"
    cloud_run_runtime_timeout_seconds: int = Field(default=1800, ge=60, le=7200)
    cloud_run_runtime_factory_timeout_seconds: int = Field(default=3600, ge=300, le=7200)
    runtime_image_repository: str = ""
    runtime_worker_service_account: str = ""
    runtime_build_service_account: str = ""
    runtime_worker_coverup_model: str = "vertex_ai/gemini-3.6-flash"
    runtime_bundle_protocol_version: int = Field(default=MINIMUM_RUNTIME_PROTOCOL_VERSION, ge=1)
    gepa_max_concurrency: int = Field(default=10, ge=1, le=32)
    gepa_repeat_tests: int = Field(default=5, ge=0, le=20)
    gepa_evaluation_replicates: int = Field(default=1, ge=1, le=10)
    final_evaluation_replicates: int = Field(default=2, ge=1, le=10)
    max_analysis_python_files: int = Field(default=5000, ge=1, le=20000)
    max_analysis_uncompressed_bytes: int = Field(default=50 * 1024 * 1024, ge=1024)
    signed_url_ttl_seconds: int = Field(default=900, ge=60, le=3600)
    max_upload_bytes: int = Field(default=100 * 1024 * 1024, ge=1024)
    local_upload_dir: str = "./data/uploads"
    sample_repos_dir: str = "../src/sample_repo"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def optimize_model_allowlist_values(self) -> set[str]:
        return {model.strip() for model in self.optimize_model_allowlist.split(",") if model.strip()}

    def resolve_app_path(self, value: str) -> Path:
        """Resolve local app paths independently of the process working directory."""
        path = Path(value).expanduser()
        return path.resolve() if path.is_absolute() else (APP_DIRECTORY / path).resolve()

    @property
    def local_upload_path(self) -> Path:
        return self.resolve_app_path(self.local_upload_dir)

    @property
    def sample_repos_path(self) -> Path:
        return self.resolve_app_path(self.sample_repos_dir)

    @property
    def cloud_run_runtime_jobs(self) -> dict[str, str]:
        """Return explicitly deployed admission jobs keyed by Python minor."""
        configured = {
            "3.10": self.cloud_run_runtime_job_py310.strip(),
            "3.11": self.cloud_run_runtime_job_py311.strip(),
            "3.12": self.cloud_run_runtime_job_py312.strip() or self.cloud_run_runtime_job.strip(),
            "3.13": self.cloud_run_runtime_job_py313.strip(),
        }
        return {version: job for version, job in configured.items() if job}

    @property
    def project_runtime_image_repository(self) -> str:
        configured = self.runtime_image_repository.strip()
        return configured or (
            f"{self.cloud_tasks_location}-docker.pkg.dev/{self.gcp_project_id}/promptopt/project-runtimes"
        )

    @property
    def project_runtime_worker_service_account(self) -> str:
        configured = self.runtime_worker_service_account.strip()
        return configured or f"promptopt-runner@{self.gcp_project_id}.iam.gserviceaccount.com"

    @property
    def project_runtime_build_service_account(self) -> str:
        configured = self.runtime_build_service_account.strip()
        return configured or f"promptopt-runtime-builder@{self.gcp_project_id}.iam.gserviceaccount.com"

    @model_validator(mode="after")
    def validate_production_backends(self):
        if self.app_env == "production":
            if self.auth_mode != "firebase":
                raise ValueError("AUTH_MODE=firebase is required in production")
            if self.repository_backend != "firestore":
                raise ValueError("REPOSITORY_BACKEND=firestore is required in production")
            if self.storage_backend != "gcs" or not self.gcs_bucket:
                raise ValueError("STORAGE_BACKEND=gcs and GCS_BUCKET are required in production")
            if not self.gcp_service_account_email:
                raise ValueError("GCP_SERVICE_ACCOUNT_EMAIL is required in production")
            if self.analysis_dispatcher != "cloud_tasks":
                raise ValueError("ANALYSIS_DISPATCHER=cloud_tasks is required in production")
            if not self.analysis_worker_url or not self.analysis_task_audience:
                raise ValueError("ANALYSIS_WORKER_URL and ANALYSIS_TASK_AUDIENCE are required in production")
            if self.experiment_dispatcher != "cloud_tasks":
                raise ValueError("EXPERIMENT_DISPATCHER=cloud_tasks is required in production")
            if not self.experiment_worker_url or not self.experiment_task_audience:
                raise ValueError("EXPERIMENT_WORKER_URL and EXPERIMENT_TASK_AUDIENCE are required in production")
            if self.optimization_execution_backend != "cloud_run_job" or not self.cloud_run_gepa_job:
                raise ValueError("OPTIMIZATION_EXECUTION_BACKEND=cloud_run_job and CLOUD_RUN_GEPA_JOB are required")
            if not self.cloud_run_test_generation_job:
                raise ValueError("CLOUD_RUN_TEST_GENERATION_JOB is required")
            if self.runtime_execution_backend != "cloud_run_job" or not self.cloud_run_runtime_job:
                raise ValueError("RUNTIME_EXECUTION_BACKEND=cloud_run_job and CLOUD_RUN_RUNTIME_JOB are required")
            if not self.cloud_run_runtime_factory_job:
                raise ValueError("CLOUD_RUN_RUNTIME_FACTORY_JOB is required")
            if not self.admin_vertexai_project.strip():
                raise ValueError("ADMIN_VERTEXAI_PROJECT is required in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
