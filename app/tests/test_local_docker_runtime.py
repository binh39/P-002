import json
from subprocess import CompletedProcess

import pytest
from cloud.sandbox_dependency_plan import build_dependency_plan
from pydantic import ValidationError

from backend.config import Settings
from backend.infrastructure.storage import LocalObjectStorage
from backend.modules.projects.local_docker_runtime import LocalDockerRuntimePreparer


def test_local_docker_runner_uses_locked_project_native_tooling(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        """
[project]
name = "local-runtime-fixture"
version = "1.0.0"
requires-python = ">=3.12"
dependencies = []

[dependency-groups]
test = ["pytest==9.1.1", "coverage==7.10.7"]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (project / "uv.lock").write_text(
        """
version = 1
revision = 1
requires-python = ">=3.12"

[[package]]
name = "coverage"
version = "7.10.7"

[[package]]
name = "pytest"
version = "9.1.1"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    runner = LocalDockerRuntimePreparer(
        storage=LocalObjectStorage(str(tmp_path / "uploads"), "/api/v1"),
        image="promptopt-sandbox:py3.12",
        root=tmp_path / "runtime",
    )

    identity = runner._runner_identity(project, build_dependency_plan(project))

    assert identity.profile == "project_native"
    assert identity.pytest_version == "9.1.1"
    assert identity.coverage_version == "7.10.7"


def test_local_docker_health_requires_matching_image_contract(tmp_path):
    digest = "sha256:" + "a" * 64
    responses = iter(
        (
            CompletedProcess([], 0, stdout=digest + "\n", stderr=""),
            CompletedProcess(
                [],
                0,
                stdout=json.dumps(
                    {
                        "python_minor": "3.12",
                        "forbidden_modules_present": [],
                        "managed_pytest_version": "9.1.1",
                        "managed_coverage_version": "7.15.3",
                    }
                ),
                stderr="",
            ),
        )
    )

    def command_runner(*args, **kwargs):
        del args, kwargs
        return next(responses)

    runner = LocalDockerRuntimePreparer(
        storage=LocalObjectStorage(str(tmp_path / "uploads"), "/api/v1"),
        image="promptopt-sandbox:py3.12",
        root=tmp_path / "runtime",
        command_runner=command_runner,
        health_ttl_seconds=60,
    )

    assert runner.is_healthy() is True
    assert runner.is_healthy() is True


def test_local_docker_backend_is_development_only(tmp_path):
    with pytest.raises(ValidationError, match="development-only"):
        Settings(
            _env_file=None,
            app_env="test",
            storage_backend="local",
            runtime_execution_backend="local_docker",
            local_runtime_dir=str(tmp_path / "runtime"),
        )


def test_local_docker_backend_requires_local_storage(tmp_path):
    with pytest.raises(ValidationError, match="requires STORAGE_BACKEND=local"):
        Settings(
            _env_file=None,
            app_env="development",
            storage_backend="gcs",
            runtime_execution_backend="local_docker",
            local_runtime_dir=str(tmp_path / "runtime"),
        )
