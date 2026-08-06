from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "PromptOpt API"
    app_env: Literal["development", "production", "test"] = "development"
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_host: str = "0.0.0.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: str = "http://localhost:5173,https://vinaip002.web.app"
    api_prefix: str = "/api/v1"

    # Authentication and Google Cloud
    auth_mode: Literal["disabled", "firebase"] = "disabled"
    repository_backend: Literal["memory", "firestore"] = "memory"
    storage_backend: Literal["local", "gcs"] = "local"
    analysis_dispatcher: Literal["inline", "cloud_tasks"] = "inline"
    gcp_project_id: str = "vinaip002"
    gcp_service_account_email: str = ""
    gcs_bucket: str = ""
    cloud_tasks_location: str = "asia-southeast1"
    cloud_tasks_queue: str = "promptopt-analysis"
    analysis_worker_url: str = ""
    analysis_task_audience: str = ""
    baseline_dispatcher: Literal["inline", "cloud_tasks"] = "inline"
    baseline_cloud_tasks_queue: str = "promptopt-baseline"
    baseline_worker_url: str = ""
    baseline_task_audience: str = ""
    baseline_execution_backend: Literal["disabled", "docker", "cloud_run_job"] = "disabled"
    baseline_runner_image: str = "promptopt-coverup-runner:local"
    cloud_run_runner_job: str = "promptopt-coverup-runner"
    cloud_run_runner_timeout_seconds: int = Field(default=900, ge=60, le=3600)
    max_runner_files: int = Field(default=10000, ge=1, le=50000)
    max_runner_uncompressed_bytes: int = Field(default=100 * 1024 * 1024, ge=1024)
    baseline_runner_network: str = "none"
    optimize_model: str = ""
    optimize_model_allowlist: str = "vertex_ai/gemini-3.6-flash"
    gepa_max_metric_calls: int = Field(default=30, ge=3, le=1000)
    final_evaluation_replicates: int = Field(default=2, ge=1, le=10)
    max_analysis_python_files: int = Field(default=5000, ge=1, le=20000)
    max_analysis_uncompressed_bytes: int = Field(default=50 * 1024 * 1024, ge=1024)
    signed_url_ttl_seconds: int = Field(default=900, ge=60, le=3600)
    max_upload_bytes: int = Field(default=100 * 1024 * 1024, ge=1024)
    local_upload_dir: str = "./data/uploads"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def optimize_model_allowlist_values(self) -> set[str]:
        return {model.strip() for model in self.optimize_model_allowlist.split(",") if model.strip()}

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
            if self.baseline_dispatcher != "cloud_tasks":
                raise ValueError("BASELINE_DISPATCHER=cloud_tasks is required in production")
            if not self.baseline_worker_url or not self.baseline_task_audience:
                raise ValueError("BASELINE_WORKER_URL and BASELINE_TASK_AUDIENCE are required in production")
            if self.baseline_execution_backend != "cloud_run_job" or not self.cloud_run_runner_job:
                raise ValueError("BASELINE_EXECUTION_BACKEND=cloud_run_job and CLOUD_RUN_RUNNER_JOB are required")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
