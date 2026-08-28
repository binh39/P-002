import pytest
from pydantic import ValidationError

from backend.config import APP_DIRECTORY, Settings
from backend.modules.projects.schemas import MINIMUM_RUNTIME_PROTOCOL_VERSION


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
        "runtime_execution_backend": "cloud_run_job",
        "cloud_run_runtime_job": "runtime-preparer",
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
    assert settings.runtime_execution_backend == "cloud_run_job"
    assert settings.runtime_bundle_protocol_version == MINIMUM_RUNTIME_PROTOCOL_VERSION
    assert settings.gcp_project_id == "project-7df9f963-9fe0-4b76-b3d"
    assert settings.admin_vertexai_project == "project-a2f7084e-90ac-4bfc-84b"


def test_production_requires_cloud_gepa_execution_backend():
    with pytest.raises(ValidationError, match="OPTIMIZATION_EXECUTION_BACKEND=cloud_run_job"):
        production_settings(optimization_execution_backend="inline")


def test_production_requires_admin_vertexai_project():
    with pytest.raises(ValidationError, match="ADMIN_VERTEXAI_PROJECT is required"):
        production_settings(admin_vertexai_project=" ")


def test_production_requires_runtime_preparation_job():
    with pytest.raises(ValidationError, match="RUNTIME_EXECUTION_BACKEND=cloud_run_job"):
        production_settings(runtime_execution_backend="disabled")


def test_production_generic_worker_does_not_require_runtime_image_factory_job():
    settings = production_settings(cloud_run_runtime_factory_job="")
    assert settings.runtime_project_image_mode == "generic_worker_bundle"


def test_production_project_image_mode_requires_factory_job():
    with pytest.raises(ValidationError, match="CLOUD_RUN_RUNTIME_FACTORY_JOB is required"):
        production_settings(cloud_run_runtime_factory_job="", runtime_project_image_mode="project_image")


def test_project_runtime_resources_default_to_dedicated_accounts_and_repository():
    settings = production_settings()

    assert settings.project_runtime_image_repository.endswith("/promptopt/project-runtimes")
    assert settings.project_runtime_worker_service_account.startswith("promptopt-runner@")
    assert settings.project_runtime_build_service_account.startswith("promptopt-runtime-builder@")


def test_local_paths_are_resolved_from_app_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    settings = Settings(_env_file=None)

    assert settings.local_upload_path == APP_DIRECTORY / "data" / "uploads"
    assert settings.sample_repos_path == APP_DIRECTORY.parent / "src" / "sample_repo"
