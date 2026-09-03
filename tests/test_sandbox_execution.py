import hashlib
import json
import os
import subprocess
import sys
import tarfile
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from cloud import sandbox_pytest_plugin
from cloud.sandbox_builder import ArtifactManifest, ImageIdentity, RunnerIdentity
from cloud.sandbox_contract import (
    CoverageMode,
    DependencyMode,
    DependencyPolicy,
    FailureStage,
    ResourceLimits,
    RunKind,
    RunnerProfile,
    RunSpec,
    SandboxSpec,
    SandboxStatus,
)
from cloud.sandbox_execution import clean_execution_workspace, execute_run
from cloud.sandbox_executor import (
    DockerExecutionRequest,
    DockerSandboxExecutor,
    SandboxExecutorError,
)
from cloud.sandbox_runner_profiles import SANDBOX_MANAGED_COVERAGE, SANDBOX_MANAGED_PYTEST


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _managed_artifact(root: Path, fingerprint: str = "a" * 64) -> tuple[Path, Path]:
    environment = root / "environment"
    python = environment / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    python.parent.mkdir(parents=True)
    python.write_bytes(b"managed-runner-placeholder")
    archive = root / "environment.tar.gz"
    with tarfile.open(archive, "w:gz") as stream:
        stream.add(environment / "venv", arcname="venv")
    empty_inventory_hash = hashlib.sha256(b"[]").hexdigest()
    manifest = ArtifactManifest(
        fingerprint=fingerprint,
        artifact_sha256=_sha256(archive),
        artifact_size=archive.stat().st_size,
        dependency_plan_fingerprint="b" * 64,
        image=ImageIdentity("3.12", "3.12.14", "linux", "x86_64", "sha256:" + "c" * 64),
        runner=RunnerIdentity(
            RunnerProfile.SANDBOX_MANAGED.value,
            SANDBOX_MANAGED_PYTEST,
            SANDBOX_MANAGED_COVERAGE,
        ),
        inventory=(),
        inventory_sha256=empty_inventory_hash,
        created_at_epoch=1,
        last_used_at_epoch=1,
    )
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest.as_dict()), encoding="utf-8")
    return archive, manifest_path


def _project(root: Path, test_body: str) -> Path:
    source = root / "source"
    package = source / "src" / "demo"
    tests = source / "generated_tests"
    package.mkdir(parents=True)
    tests.mkdir()
    (package / "__init__.py").write_text(
        "def classify(value):\n    if value > 0:\n        return 'positive'\n    return 'other'\n",
        encoding="utf-8",
    )
    (tests / "conftest.py").write_text(
        "import pytest\n\n@pytest.fixture\ndef positive_value():\n    return 2\n",
        encoding="utf-8",
    )
    (tests / "test_generated.py").write_text(test_body, encoding="utf-8")
    (source / "pyproject.toml").write_text(
        "[tool.coverage.report]\nfail_under = 100\n[tool.pytest.ini_options]\nmarkers = ['sandbox: generated']\n",
        encoding="utf-8",
    )
    return source


def _spec(*, output_bytes: int = 1024 * 1024) -> SandboxSpec:
    return SandboxSpec(
        project_id="managed-demo",
        archive_sha256="d" * 64,
        requested_python="3.12",
        detected_python="3.12",
        source_directory="src/demo",
        test_directory="generated_tests",
        dependency_policy=DependencyPolicy(DependencyMode.NONE),
        runner_profile=RunnerProfile.SANDBOX_MANAGED,
        coverage_mode=CoverageMode.STATEMENT_AND_BRANCH,
        allowed_environment_variables=("PYTHONHASHSEED", "TZ"),
        resource_limits=ResourceLimits(timeout_seconds=30, maximum_output_bytes=output_bytes),
    )


def _run(fingerprint: str = "a" * 64) -> RunSpec:
    return RunSpec(
        run_id="managed-candidate",
        kind=RunKind.CANDIDATE,
        environment_fingerprint=fingerprint,
        test_paths=("generated_tests/test_generated.py",),
        source_file="src/demo/__init__.py",
        symbol="classify",
    )


def _execute(tmp_path: Path, test_body: str, *, output_bytes: int = 1024 * 1024):
    artifact_root = tmp_path / "artifact"
    artifact_root.mkdir(parents=True)
    archive, manifest = _managed_artifact(artifact_root)
    source = _project(tmp_path, test_body)
    output = tmp_path / "output"
    workspace = tmp_path / "workspace"
    result = execute_run(
        _spec(output_bytes=output_bytes),
        _run(),
        manifest_path=manifest,
        archive_path=archive,
        source_root=source,
        output_root=output,
        workspace_root=workspace,
        managed_python=Path(sys.executable),
    )
    return result, output, workspace


def test_managed_runner_executes_generated_test_and_ignores_project_fail_under(tmp_path):
    result, output, _ = _execute(
        tmp_path,
        "import pytest\nfrom demo import classify\n\n@pytest.mark.sandbox\ndef test_generated(positive_value):\n"
        "    assert classify(positive_value) == 'positive'\n",
    )

    assert result.status == SandboxStatus.SUCCEEDED, (
        result.failure_stage,
        result.error_code,
        result.stderr,
        result.stdout,
    )
    assert result.runner_profile == RunnerProfile.SANDBOX_MANAGED
    assert result.pytest_version == SANDBOX_MANAGED_PYTEST
    assert result.coverage_version == SANDBOX_MANAGED_COVERAGE
    assert result.test_counts.passed == 1
    assert result.coverage.total_statements > 0
    assert result.coverage.covered_statements > 0
    assert result.coverage_artifact == "coverage/normalized.json"
    normalized = json.loads((output / result.coverage_artifact).read_text(encoding="utf-8"))
    assert normalized["target"] == {"source_file": "src/demo/__init__.py", "symbol": "classify"}


def test_test_failure_keeps_denominator_but_forces_covered_units_to_zero(tmp_path):
    result, _, _ = _execute(
        tmp_path,
        "from demo import classify\n\ndef test_generated():\n    assert classify(2) == 'wrong'\n",
    )

    assert result.status == SandboxStatus.FAILED
    assert result.failure_stage == FailureStage.TEST
    assert result.error_code == "TESTS_FAILED"
    assert result.exit_code == 1
    assert result.coverage.total_statements > 0
    assert result.coverage.covered_statements == 0
    assert result.coverage.covered_branches == 0


def test_no_tests_collected_still_exports_zero_coverage_with_denominator(tmp_path):
    result, _, _ = _execute(tmp_path, "VALUE = 1\n")

    assert result.status == SandboxStatus.SUCCEEDED, (
        result.failure_stage,
        result.error_code,
        result.stderr,
        result.stdout,
    )
    assert result.exit_code == 5
    assert result.test_counts.collected == 0
    assert result.coverage.total_statements > 0
    assert result.coverage.covered_statements == 0


def test_collection_error_has_distinct_stage_and_code(tmp_path):
    result, _, _ = _execute(tmp_path, "def broken(:\n    pass\n")

    assert result.status == SandboxStatus.FAILED
    assert result.failure_stage == FailureStage.COLLECT, (
        result.error_code,
        result.stderr,
        result.stdout,
    )
    assert result.error_code == "TEST_COLLECTION_FAILED"


def test_collection_network_failure_has_actionable_code(tmp_path):
    result, _, _ = _execute(
        tmp_path,
        "raise OSError('Network is unreachable')\n",
    )

    assert result.status == SandboxStatus.FAILED
    assert result.failure_stage == FailureStage.COLLECT
    assert result.error_code == "EXECUTION_NETWORK_DENIED"


def test_execution_output_redacts_credentials(tmp_path):
    result, _, _ = _execute(
        tmp_path,
        "def test_secret():\n    raise AssertionError('API_TOKEN=do-not-leak')\n",
    )

    assert "do-not-leak" not in result.stdout
    assert "do-not-leak" not in result.stderr


def test_output_is_bounded(tmp_path):
    result, _, _ = _execute(
        tmp_path,
        "def test_noisy():\n    print('x' * 10000)\n    assert True\n",
        output_bytes=1024,
    )

    assert len(result.stdout.encode()) <= 1024


def test_normalized_coverage_is_reproducible_for_same_fingerprint(tmp_path):
    body = "from demo import classify\n\ndef test_generated():\n    assert classify(1) == 'positive'\n"
    first, first_output, _ = _execute(tmp_path / "first", body)
    second, second_output, _ = _execute(tmp_path / "second", body)

    assert first.coverage == second.coverage
    assert (first_output / "coverage/normalized.json").read_bytes() == (
        second_output / "coverage/normalized.json"
    ).read_bytes()


def test_cleanup_removes_only_execution_workspace(tmp_path):
    workspace = tmp_path / "execution"
    workspace.mkdir()
    (workspace / "temporary").write_text("data", encoding="utf-8")
    sibling = tmp_path / "keep"
    sibling.write_text("keep", encoding="utf-8")

    clean_execution_workspace(workspace)

    assert not workspace.exists()
    assert sibling.read_text(encoding="utf-8") == "keep"


def test_pytest_count_plugin_distinguishes_same_nodeid_in_repeated_files(monkeypatch):
    monkeypatch.setattr(
        sandbox_pytest_plugin,
        "_counts",
        {"collected": 2, "passed": 0, "failed": 0, "skipped": 0},
    )
    for filename in ("test_candidate_r0.py", "test_candidate_r1.py"):
        sandbox_pytest_plugin.pytest_runtest_logreport(
            SimpleNamespace(
                fspath=filename,
                nodeid="::test_candidate",
                when="call",
                passed=True,
                failed=False,
                skipped=False,
            )
        )

    assert sandbox_pytest_plugin._counts["passed"] == 2


def test_manifest_runner_version_mismatch_is_rejected_before_tests(tmp_path):
    artifact_root = tmp_path / "artifact"
    artifact_root.mkdir()
    archive, manifest_path = _managed_artifact(artifact_root)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["runner"]["coverage_version"] = "0.0.0"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    source = _project(tmp_path, "def test_generated():\n    assert True\n")

    result = execute_run(
        _spec(),
        _run(),
        manifest_path=manifest_path,
        archive_path=archive,
        source_root=source,
        output_root=tmp_path / "output",
        workspace_root=tmp_path / "workspace",
        managed_python=Path(sys.executable),
    )

    assert result.error_code == "RUNNER_PROFILE_MISMATCH"
    assert result.failure_stage == FailureStage.COLLECT


def _docker_request(tmp_path: Path, *, environment=None) -> DockerExecutionRequest:
    archive, manifest = _managed_artifact(tmp_path / "artifact")
    source = _project(tmp_path, "def test_generated():\n    assert True\n")
    output = tmp_path / "output"
    return DockerExecutionRequest(
        image_digest="sha256:" + "c" * 64,
        artifact_archive=archive,
        artifact_manifest=manifest,
        source_root=source,
        output_root=output,
        sandbox_spec=_spec(),
        run_spec=_run(),
        environment=environment or {},
    )


def test_docker_command_enforces_isolation_and_resource_limits(tmp_path):
    request = _docker_request(tmp_path)
    control = tmp_path / "control"
    control.mkdir()
    spec_path = control / "spec.json"
    run_path = control / "run.json"
    spec_path.write_text("{}", encoding="utf-8")
    run_path.write_text("{}", encoding="utf-8")

    command = DockerSandboxExecutor().build_command(request, spec_path=spec_path, run_path=run_path)

    joined = " ".join(command)
    assert "--network none" in joined
    assert "--read-only" in command
    assert "--cap-drop ALL" in joined
    assert "--security-opt no-new-privileges" in joined
    assert "--pids-limit 128" in joined
    assert "--cpus 1" in joined
    assert "--memory 2048m" in joined
    assert "target=/project,readonly" in joined
    assert "target=/output" in joined
    assert "/var/run/docker.sock" not in joined
    assert "target=/home" not in joined


def test_docker_executor_rejects_credentials_even_if_contract_lists_them(tmp_path):
    request = _docker_request(tmp_path, environment={"AWS_SECRET_ACCESS_KEY": "secret"})
    request = replace(
        request,
        sandbox_spec=replace(
            request.sandbox_spec,
            allowed_environment_variables=("AWS_SECRET_ACCESS_KEY",),
        ),
    )

    with pytest.raises(SandboxExecutorError, match="not allowlisted"):
        DockerSandboxExecutor().build_command(
            request,
            spec_path=request.artifact_manifest,
            run_path=request.artifact_manifest,
        )


def test_docker_executor_parses_only_structured_last_line(tmp_path):
    request = _docker_request(tmp_path)
    payload = {
        "protocol_version": 1,
        "run_id": request.run_spec.run_id,
        "status": "succeeded",
        "environment_fingerprint": request.run_spec.environment_fingerprint,
    }
    runner = lambda *args, **kwargs: SimpleNamespace(  # noqa: E731
        returncode=0,
        stdout="agent diagnostic\n" + json.dumps(payload),
        stderr="",
    )

    result = DockerSandboxExecutor(runner=runner).execute(request)

    assert result.status == SandboxStatus.SUCCEEDED
    assert not (request.output_root / ".sandbox-control").exists()


def test_docker_executor_rejects_image_digest_mismatch_before_run(tmp_path):
    request = replace(_docker_request(tmp_path), image_digest="sha256:" + "e" * 64)
    called = False

    def runner(*args, **kwargs):
        nonlocal called
        called = True

    with pytest.raises(SandboxExecutorError, match="image digest"):
        DockerSandboxExecutor(runner=runner).execute(request)

    assert not called


def test_outer_timeout_force_removes_only_named_execution_container(tmp_path):
    request = _docker_request(tmp_path)
    calls = []

    def runner(command, **kwargs):
        calls.append((command, kwargs))
        if command[1] == "run":
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    with pytest.raises(SandboxExecutorError, match="wall-clock"):
        DockerSandboxExecutor(runner=runner).execute(request)

    run_command = calls[0][0]
    container_name = run_command[run_command.index("--name") + 1]
    assert container_name.startswith("promptopt-sandbox-")
    assert calls[1][0] == ["docker", "rm", "--force", container_name]
    assert not (request.output_root / ".sandbox-control").exists()
