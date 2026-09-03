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
    admin_vertexai_project: str = "vinbuildphase"
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
    runtime_execution_backend: Literal["disabled", "cloud_run_job", "local_docker"] = "disabled"
    cloud_run_runtime_job: str = "promptopt-runtime-preparer"
    cloud_run_runtime_timeout_seconds: int = Field(default=1800, ge=60, le=7200)
    local_sandbox_image: str = "promptopt-sandbox:py3.12"
    local_runtime_dir: str = "./data/local-runtime"
    local_docker_executable: str = "docker"
    runtime_bundle_protocol_version: int = Field(default=MINIMUM_RUNTIME_PROTOCOL_VERSION, ge=1)
    project_sandbox_v2: bool = False
    project_sandbox_rollout_mode: Literal["disabled", "shadow", "canary", "enabled"] = "disabled"
    sandbox_runtime_execution_backend: Literal["disabled", "cloud_run_job", "local_docker"] = "disabled"
    sandbox_cloud_run_runtime_job: str = "promptopt-project-sandbox-v2"
    sandbox_canary_percent: int = Field(default=0, ge=0, le=100)
    sandbox_canary_python_versions: str = "3.12"
    sandbox_advertised_python_versions: str = ""
    sandbox_rollback_window_days: int = Field(default=14, ge=1, le=90)
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

    @property
    def sandbox_canary_python_version_values(self) -> set[str]:
        return {version.strip() for version in self.sandbox_canary_python_versions.split(",") if version.strip()}

    @property
    def sandbox_advertised_python_version_values(self) -> set[str]:
        return {version.strip() for version in self.sandbox_advertised_python_versions.split(",") if version.strip()}

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
    def local_runtime_path(self) -> Path:
        return self.resolve_app_path(self.local_runtime_dir)

    @model_validator(mode="after")
    def validate_production_backends(self):
        if self.runtime_execution_backend == "local_docker" and self.app_env != "development":
            raise ValueError("RUNTIME_EXECUTION_BACKEND=local_docker is development-only")
        if self.runtime_execution_backend == "local_docker" and self.storage_backend != "local":
            raise ValueError("RUNTIME_EXECUTION_BACKEND=local_docker requires STORAGE_BACKEND=local")
        if self.sandbox_runtime_execution_backend == "local_docker" and self.app_env != "development":
            raise ValueError("SANDBOX_RUNTIME_EXECUTION_BACKEND=local_docker is development-only")
        if self.sandbox_runtime_execution_backend == "local_docker" and self.storage_backend != "local":
            raise ValueError("SANDBOX_RUNTIME_EXECUTION_BACKEND=local_docker requires STORAGE_BACKEND=local")
        if self.project_sandbox_rollout_mode != "disabled" and not self.project_sandbox_v2:
            raise ValueError("PROJECT_SANDBOX_V2=true is required for sandbox rollout")
        if self.project_sandbox_v2 and self.project_sandbox_rollout_mode != "disabled":
            if self.runtime_execution_backend == "disabled":
                raise ValueError("RUNTIME_EXECUTION_BACKEND must keep the legacy executor during rollout")
            if self.sandbox_runtime_execution_backend == "disabled":
                raise ValueError("SANDBOX_RUNTIME_EXECUTION_BACKEND is required for sandbox rollout")
            if self.project_sandbox_rollout_mode == "canary" and self.sandbox_canary_percent == 0:
                raise ValueError("SANDBOX_CANARY_PERCENT must be positive in canary mode")
        supported_versions = {"3.10", "3.11", "3.12", "3.13"}
        if not self.sandbox_canary_python_version_values <= supported_versions:
            raise ValueError("SANDBOX_CANARY_PYTHON_VERSIONS contains an unsupported Python minor")
        if not self.sandbox_advertised_python_version_values <= supported_versions:
            raise ValueError("SANDBOX_ADVERTISED_PYTHON_VERSIONS contains an unsupported Python minor")
        if self.sandbox_advertised_python_version_values and self.project_sandbox_rollout_mode != "enabled":
            raise ValueError("Sandbox Python versions may be advertised only after rollout mode is enabled")
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
            if self.project_sandbox_v2 and self.project_sandbox_rollout_mode != "disabled":
                if self.sandbox_runtime_execution_backend != "cloud_run_job" or not self.sandbox_cloud_run_runtime_job:
                    raise ValueError(
                        "SANDBOX_RUNTIME_EXECUTION_BACKEND=cloud_run_job and SANDBOX_CLOUD_RUN_RUNTIME_JOB are required"
                    )
            if not self.admin_vertexai_project.strip():
                raise ValueError("ADMIN_VERTEXAI_PROJECT is required in production")
            if not self.admin_vertexai_project.strip():
                raise ValueError("ADMIN_VERTEXAI_PROJECT is required in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
