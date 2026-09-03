from __future__ import annotations

import hashlib
import json
import tarfile
from pathlib import Path

import pytest

from cloud.sandbox_builder import ArtifactManifest, ImageIdentity, RunnerIdentity
from cloud.sandbox_contract import (
    CoverageSummary,
    RunKind,
    RunnerProfile,
    SandboxResult,
    SandboxStatus,
)
from cloud.sandbox_contract import TestCounts as SandboxTestCounts
from src.optimization.cli import _resolve_sandbox_environments
from src.optimization.gepa import _evaluation_digest, require_paired_environment_fingerprints
from src.optimization.models import (
    ExperimentConfig,
    ProjectLayout,
    SandboxEnvironment,
    SymbolTarget,
)
from src.optimization.runner import CoverUpExperimentRunner
from src.optimization.sandbox import OptimizerSandboxClient


def _environment(root: Path, fingerprint: str = "a" * 64) -> SandboxEnvironment:
    source = root / "project"
    package = source / "src" / "demo"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(
        "def classify(value):\n    if value > 0:\n        return 'positive'\n    return 'other'\n",
        encoding="utf-8",
    )
    artifact = root / "artifact"
    artifact.mkdir()
    archive = artifact / "environment.tar.gz"
    placeholder = root / "placeholder" / "venv" / "bin"
    placeholder.mkdir(parents=True)
    (placeholder / "python").write_text("placeholder", encoding="utf-8")
    with tarfile.open(archive, "w:gz") as stream:
        stream.add(placeholder.parent, arcname="venv")
    image_digest = "sha256:" + "b" * 64
    manifest = ArtifactManifest(
        fingerprint=fingerprint,
        artifact_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
        artifact_size=archive.stat().st_size,
        dependency_plan_fingerprint="c" * 64,
        image=ImageIdentity("3.12", "3.12.14", "linux", "x86_64", image_digest),
        runner=RunnerIdentity("sandbox_managed", "9.1.1", "7.15.3"),
        inventory=(),
        inventory_sha256=hashlib.sha256(b"[]").hexdigest(),
        created_at_epoch=1,
        last_used_at_epoch=1,
    )
    manifest_path = artifact / "manifest.json"
    manifest_path.write_text(json.dumps(manifest.as_dict()), encoding="utf-8")
    return SandboxEnvironment(
        image_digest=image_digest,
        artifact_archive=archive,
        artifact_manifest=manifest_path,
        source_root=source,
        source_directory="src/demo",
        requested_python="3.12",
        runner_profile="sandbox_managed",
    )


class FakeExecutor:
    def __init__(self) -> None:
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        coverage_path = request.output_root / "coverage" / "normalized.json"
        coverage_path.parent.mkdir(parents=True)
        coverage_path.write_text(
            json.dumps(
                {
                    "environment_fingerprint": request.run_spec.environment_fingerprint,
                    "target": {
                        "source_file": request.run_spec.source_file,
                        "symbol": request.run_spec.symbol,
                    },
                    "files": [
                        {
                            "path": request.run_spec.source_file,
                            "executed_lines": [1, 2, 3],
                            "missing_lines": [4],
                            "executed_branches": [[2, 3]],
                            "missing_branches": [[2, 4]],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return SandboxResult(
            run_id=request.run_spec.run_id,
            status=SandboxStatus.SUCCEEDED,
            environment_fingerprint=request.run_spec.environment_fingerprint,
            exit_code=0,
            test_counts=SandboxTestCounts(collected=1, passed=1),
            coverage=CoverageSummary(3, 4, 1, 2),
            coverage_artifact="coverage/normalized.json",
            runner_profile=RunnerProfile.SANDBOX_MANAGED,
            pytest_version="9.1.1",
            coverage_version="7.15.3",
        )


def test_optimizer_sandbox_client_sends_source_identity_and_generated_tests(tmp_path):
    environment = _environment(tmp_path)
    tests = tmp_path / "generated"
    tests.mkdir()
    generated = tests / "test_candidate.py"
    generated.write_text("from demo import classify\ndef test_it(): assert classify(1) == 'positive'\n", encoding="utf-8")
    project_tests = tmp_path / "project-tests"
    project_tests.mkdir()
    (project_tests / "conftest.py").write_text("VALUE = 1\n", encoding="utf-8")
    executor = FakeExecutor()
    client = OptimizerSandboxClient({"demo": environment}, executor=executor)
    target = SymbolTarget("demo", "src/demo/__init__.py", "classify", "validation")

    evaluation = client.evaluate(
        target,
        [generated],
        project_tests=project_tests,
        run_root=tmp_path / "run",
        run_id="candidate-demo",
        kind=RunKind.CANDIDATE,
    )

    request = executor.requests[0]
    assert request.run_spec.source_file == target.source_file
    assert request.run_spec.symbol == target.symbol
    assert request.run_spec.environment_fingerprint == "a" * 64
    assert request.tests_root != request.source_root
    assert (request.tests_root / "conftest.py").is_file()
    assert evaluation.coverage.num_statements == 4
    assert evaluation.coverage.num_branches == 2


def test_configured_runner_uses_sandbox_for_optimizer_experiment(tmp_path, monkeypatch):
    environment = _environment(tmp_path)
    executor = FakeExecutor()
    tests_dir = tmp_path / "project-tests"
    tests_dir.mkdir()
    config = ExperimentConfig(
        project_root=tmp_path,
        package_dir=environment.source_root / "src" / "demo",
        tests_dir=tests_dir,
        artifacts_dir=tmp_path / "artifacts",
        coverup_model="unused",
        sandbox_environments={"demo": environment},
        sandbox_executor=executor,
    )
    monkeypatch.setattr(
        "src.optimization.runner.run_coverage",
        lambda **kwargs: pytest.fail("host coverage must not run in sandbox mode"),
    )
    runner = CoverUpExperimentRunner(config)
    target = SymbolTarget("demo", "src/demo/__init__.py", "classify", "train")

    result = runner.evaluate_optimizer_test(
        target,
        "from demo import classify\ndef test_it(): assert classify(1) == 'positive'\n",
        experiment_id="sandbox-teacher",
    )

    assert result["pytest_passed"] is True
    assert result["environment_fingerprint"] == "a" * 64
    assert len(executor.requests) == 1


def test_paired_scoring_rejects_environment_fingerprint_mismatch():
    target = {"project": "demo", "source_file": "demo.py", "symbol": "f", "split": "test"}
    baseline = [{"target": target, "environment_fingerprint": "a" * 64}]
    candidate = [{"target": target, "environment_fingerprint": "b" * 64}]

    with pytest.raises(RuntimeError, match="Environment fingerprint mismatch"):
        require_paired_environment_fingerprints(candidate, baseline)


def test_evaluation_digest_changes_when_project_environment_changes(tmp_path):
    first = _environment(tmp_path / "first", "a" * 64)
    second = _environment(tmp_path / "second", "d" * 64)
    target = SymbolTarget("demo", "src/demo/__init__.py", "classify", "train")

    def runner(environment):
        config = ExperimentConfig(
            project_root=tmp_path,
            package_dir=environment.source_root / "src" / "demo",
            tests_dir=tmp_path,
            artifacts_dir=tmp_path / "artifacts",
            coverup_model="model",
            sandbox_environments={"demo": environment},
            sandbox_executor=FakeExecutor(),
        )
        return CoverUpExperimentRunner(config)

    assert _evaluation_digest(runner(first), [target]) != _evaluation_digest(runner(second), [target])


def test_sandbox_environment_file_must_cover_every_dataset_project(tmp_path):
    environment = _environment(tmp_path)
    config_path = tmp_path / "sandbox-environments.json"
    config_path.write_text(
        json.dumps(
            {
                "demo": {
                    "image_digest": environment.image_digest,
                    "artifact_archive": str(environment.artifact_archive),
                    "artifact_manifest": str(environment.artifact_manifest),
                    "source_root": str(environment.source_root),
                    "source_directory": environment.source_directory,
                    "requested_python": environment.requested_python,
                    "runner_profile": environment.runner_profile,
                }
            }
        ),
        encoding="utf-8",
    )
    layouts = {
        "demo": ProjectLayout(environment.source_root / "src" / "demo", tmp_path),
        "second": ProjectLayout(tmp_path, tmp_path),
    }

    with pytest.raises(ValueError, match="must match dataset projects exactly"):
        _resolve_sandbox_environments(tmp_path, layouts, config_path)
