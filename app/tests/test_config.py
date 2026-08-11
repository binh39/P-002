import pytest
from pydantic import ValidationError

from backend.config import Settings


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
        "experiment_dispatcher": "cloud_tasks",
        "experiment_worker_url": "https://api.example",
        "experiment_task_audience": "https://api.example",
        "optimization_execution_backend": "cloud_run_job",
        "cloud_run_gepa_job": "gepa-runner",
    }
    values.update(overrides)
    return Settings(**values)


def test_production_requires_cloud_tasks_experiment_dispatcher():
    with pytest.raises(ValidationError, match="EXPERIMENT_DISPATCHER=cloud_tasks"):
        production_settings(experiment_dispatcher="inline")


def test_production_cloud_run_job_configuration_is_valid():
    settings = production_settings()

    assert settings.experiment_dispatcher == "cloud_tasks"
    assert settings.optimization_execution_backend == "cloud_run_job"
    assert settings.cloud_run_gepa_timeout_seconds == 86400
    assert settings.admin_vertexai_project == "project-7df9f963-9fe0-4b76-b3d"


def test_production_requires_cloud_gepa_execution_backend():
    with pytest.raises(ValidationError, match="OPTIMIZATION_EXECUTION_BACKEND=cloud_run_job"):
        production_settings(optimization_execution_backend="inline")


def test_production_requires_admin_vertexai_project():
    with pytest.raises(ValidationError, match="ADMIN_VERTEXAI_PROJECT is required"):
        production_settings(admin_vertexai_project=" ")
