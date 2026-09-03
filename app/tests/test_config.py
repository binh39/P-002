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
    assert settings.admin_vertexai_project == "vinbuildphase"


def test_production_requires_cloud_gepa_execution_backend():
    with pytest.raises(ValidationError, match="OPTIMIZATION_EXECUTION_BACKEND=cloud_run_job"):
        production_settings(optimization_execution_backend="inline")


def test_production_requires_admin_vertexai_project():
    with pytest.raises(ValidationError, match="ADMIN_VERTEXAI_PROJECT is required"):
        production_settings(admin_vertexai_project=" ")


def test_production_requires_runtime_preparation_job():
    with pytest.raises(ValidationError, match="RUNTIME_EXECUTION_BACKEND=cloud_run_job"):
        production_settings(runtime_execution_backend="disabled")


def test_local_paths_are_resolved_from_app_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    settings = Settings(_env_file=None)

    assert settings.local_upload_path == APP_DIRECTORY / "data" / "uploads"
    assert settings.sample_repos_path == APP_DIRECTORY.parent / "src" / "sample_repo"


def test_rollout_requires_feature_flag_and_two_runners(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    with pytest.raises(ValidationError, match="PROJECT_SANDBOX_V2=true"):
        Settings(_env_file=None, project_sandbox_rollout_mode="shadow")

    with pytest.raises(ValidationError, match="legacy executor"):
        Settings(
            _env_file=None,
            project_sandbox_v2=True,
            project_sandbox_rollout_mode="shadow",
            sandbox_runtime_execution_backend="local_docker",
        )


def test_python_versions_are_advertised_only_after_full_enablement(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    with pytest.raises(ValidationError, match="advertised only after rollout mode is enabled"):
        Settings(_env_file=None, sandbox_advertised_python_versions="3.12")

    settings = Settings(
        _env_file=None,
        project_sandbox_v2=True,
        project_sandbox_rollout_mode="enabled",
        runtime_execution_backend="local_docker",
        sandbox_runtime_execution_backend="local_docker",
        sandbox_advertised_python_versions="3.12",
    )

    assert settings.sandbox_advertised_python_version_values == {"3.12"}
