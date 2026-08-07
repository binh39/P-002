import pytest
from pydantic import ValidationError

from src.config import Settings


def production_settings(**overrides):
    values = {
        "_env_file": None,
        "app_env": "production",
        "auth_mode": "firebase",
        "repository_backend": "firestore",
        "storage_backend": "gcs",
        "gcs_bucket": "private-bucket",
        "gcp_service_account_email": "api@example.iam.gserviceaccount.com",
        "analysis_dispatcher": "cloud_tasks",
        "analysis_worker_url": "https://api.example",
        "analysis_task_audience": "https://api.example",
        "baseline_dispatcher": "cloud_tasks",
        "baseline_worker_url": "https://api.example",
        "baseline_task_audience": "https://api.example",
        "baseline_execution_backend": "cloud_run_job",
        "cloud_run_runner_job": "runner",
        "optimization_execution_backend": "cloud_run_job",
        "cloud_run_gepa_job": "gepa-runner",
    }
    values.update(overrides)
    return Settings(**values)


def test_production_requires_cloud_run_job_execution_backend():
    with pytest.raises(ValidationError, match="BASELINE_EXECUTION_BACKEND=cloud_run_job"):
        production_settings(baseline_execution_backend="disabled")


def test_production_cloud_run_job_configuration_is_valid():
    settings = production_settings()

    assert settings.baseline_execution_backend == "cloud_run_job"
    assert settings.cloud_run_runner_timeout_seconds == 900
    assert settings.optimization_execution_backend == "cloud_run_job"


def test_production_requires_cloud_gepa_execution_backend():
    with pytest.raises(ValidationError, match="OPTIMIZATION_EXECUTION_BACKEND=cloud_run_job"):
        production_settings(optimization_execution_backend="inline")
