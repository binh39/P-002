import ast
import configparser
import hashlib
import io
import json
import os
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path, PurePosixPath

import pytest

from cloud.runtime_workspace import RUNTIME_TOOL_PACKAGES, RuntimeProjectSpec, prepare_environment, safe_extract_zip
from cloud.sandbox_contract import (
    ContractError,
    RunnerProfile,
    RunSpec,
    SandboxResult,
    require_matching_fingerprint,
)
from cloud.sandbox_errors import ResolverErrorKind, classify_resolver_failure
from cloud.sandbox_runner_profiles import select_runner_profile

CATALOG_PATH = Path(__file__).parent / "fixtures" / "sandbox_projects.json"
EXPECTED_CASES = {
    "py312_minimal",
    "coverage_7_10_7",
    "conflict_v1",
    "conflict_v2",
    "uv_locked",
    "poetry_locked",
    "setup_cfg_only",
    "setup_py_only",
    "conflicting_optional_groups",
    "no_runner",
    "old_runner",
    "incompatible_python",
    "no_tests",
    "coverage_fail_under",
    "pytest_addopts",
}


@pytest.fixture(scope="module")
def project_catalog() -> dict[str, dict]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def materialize(case: dict, root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for relative, content in case["files"].items():
        destination = root / PurePosixPath(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
    return root


def zip_bytes(case: dict, root_name: str = "project") -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
        for relative, content in sorted(case["files"].items()):
            entry = zipfile.ZipInfo(f"{root_name}/{relative}")
            entry.date_time = (2020, 1, 1, 0, 0, 0)
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, content.encode())
    return stream.getvalue()


def write_case_zip(path: Path, case: dict, root_name: str) -> Path:
    path.write_bytes(zip_bytes(case, root_name))
    return path


def test_fixture_catalog_is_complete_safe_and_deterministic(project_catalog):
    assert set(project_catalog) == EXPECTED_CASES
    for name, case in project_catalog.items():
        assert case["files"], name
        assert case["tags"], name
        for relative, content in case["files"].items():
            parsed = PurePosixPath(relative)
            assert not parsed.is_absolute(), (name, relative)
            assert ".." not in parsed.parts, (name, relative)
            assert isinstance(content, str), (name, relative)
        assert zip_bytes(case) == zip_bytes(case)


def test_minimal_python_project_runs_tests_offline(project_catalog, tmp_path):
    root = materialize(project_catalog["py312_minimal"], tmp_path / "minimal")
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        item for item in (str(root / "src"), environment.get("PYTHONPATH", "")) if item
    )

    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(root / "tests")],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "1 passed" in completed.stdout


def test_lock_and_manifest_fixtures_parse_without_network(project_catalog):
    uv_project = tomllib.loads(project_catalog["uv_locked"]["files"]["pyproject.toml"])
    uv_lock = tomllib.loads(project_catalog["uv_locked"]["files"]["uv.lock"])
    poetry_project = tomllib.loads(project_catalog["poetry_locked"]["files"]["pyproject.toml"])
    poetry_lock = tomllib.loads(project_catalog["poetry_locked"]["files"]["poetry.lock"])

    assert uv_project["project"]["requires-python"] == ">=3.12"
    assert uv_lock["requires-python"] == ">=3.12"
    assert poetry_project["tool"]["poetry"]["name"] == "phase1-poetry-locked"
    assert poetry_lock["metadata-version"] == "2.0"


def test_setup_cfg_and_setup_py_fixtures_are_static_and_setup_py_is_not_executed(project_catalog, tmp_path):
    parser = configparser.ConfigParser()
    parser.read_string(project_catalog["setup_cfg_only"]["files"]["setup.cfg"])
    assert parser["metadata"]["name"] == "phase1-setup-cfg"
    assert "fixture-dependency" in parser["options"]["install_requires"]

    root = materialize(project_catalog["setup_py_only"], tmp_path / "setup-py")
    tree = ast.parse((root / "setup.py").read_text(encoding="utf-8"))
    assert any(isinstance(node, ast.Call) for node in ast.walk(tree))
    assert not (root / "SETUP_EXECUTED").exists()


def test_optional_group_conflicts_are_outside_the_safe_test_group(project_catalog):
    metadata = tomllib.loads(project_catalog["conflicting_optional_groups"]["files"]["pyproject.toml"])
    groups = metadata["dependency-groups"]

    assert groups["test"] == []
    assert groups["dev"] == ["shared-dependency==1.0.0"]
    assert groups["docs"] == ["shared-dependency==2.0.0"]
    assert groups["release"] == ["shared-dependency==3.0.0"]


def test_runner_fixtures_select_managed_native_and_fallback_profiles(project_catalog):
    assert "pytest" not in project_catalog["no_runner"]["files"]["pyproject.toml"]
    managed = select_runner_profile({})
    native = select_runner_profile({"pytest": "9.1.1", "coverage": "7.10.7"})
    fallback = select_runner_profile({"pytest": "6.2.5", "coverage": "6.5.0"})

    assert managed.profile == RunnerProfile.SANDBOX_MANAGED
    assert native.profile == RunnerProfile.PROJECT_NATIVE
    assert native.coverage_version == "7.10.7"
    assert fallback.profile == RunnerProfile.COMPATIBILITY_FALLBACK
    assert fallback.error_code == "UNSUPPORTED_PROJECT_RUNNER"


def test_python_and_pytest_configuration_fixtures_are_explicit(project_catalog):
    incompatible = tomllib.loads(project_catalog["incompatible_python"]["files"]["pyproject.toml"])
    parser = configparser.ConfigParser()
    parser.read_string(project_catalog["pytest_addopts"]["files"]["pytest.ini"])

    assert incompatible["project"]["requires-python"] == ">=99"
    assert parser["pytest"]["addopts"] == "--strict-markers"
    assert "phase1" in parser["pytest"]["markers"]


def test_real_zip_fixture_is_extracted_and_inspected_by_runtime_code(project_catalog, tmp_path):
    archive = write_case_zip(
        tmp_path / "coverage-fail-under.zip",
        project_catalog["coverage_fail_under"],
        "coverage-fail-under",
    )
    first_digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert first_digest == hashlib.sha256(zip_bytes(project_catalog["coverage_fail_under"], "coverage-fail-under")).hexdigest()

    output = tmp_path / "extracted"
    safe_extract_zip(archive, output)

    extracted = output / "coverage-fail-under"
    assert (extracted / "fail_under_pkg" / "__init__.py").is_file()
    assert "fail_under = 99" in (extracted / ".coveragerc").read_text(encoding="utf-8")


def test_current_shared_resolver_reproduces_project_and_optimizer_conflict(project_catalog, tmp_path, monkeypatch):
    first = write_case_zip(tmp_path / "first.zip", project_catalog["conflict_v1"], "first")
    second = write_case_zip(tmp_path / "second.zip", project_catalog["conflict_v2"], "second")
    captured: dict[str, list[str]] = {}

    from cloud import runtime_workspace

    monkeypatch.setattr(runtime_workspace.shutil, "which", lambda name: "uv" if name == "uv" else None)

    def fake_run(result, name, command, cwd, deadline, output_limit, **kwargs):
        del result, cwd, deadline, output_limit, kwargs
        if name == "resolve shared dependencies":
            captured["command"] = command
            raise RuntimeError(
                "Dependency conflict prevented this project from joining the environment: "
                "No solution found when resolving dependencies; requirements are unsatisfiable"
            )
        return None

    monkeypatch.setattr(runtime_workspace, "_run", fake_run)
    result, python = prepare_environment(
        [
            RuntimeProjectSpec("first", first, "alpha", "tests"),
            RuntimeProjectSpec("second", second, "beta", "tests"),
        ],
        tmp_path / "shared-runtime",
    )

    assert python is None
    assert result.status == "runtime_failed"
    command = captured["command"]
    assert any("first/requirements.txt" in item.replace("\\", "/") for item in command)
    assert any("second/requirements.txt" in item.replace("\\", "/") for item in command)
    assert set(RUNTIME_TOOL_PACKAGES).issubset(command)
    assert "requirements are unsatisfiable" in (result.error or "")


def test_conflicting_dependencies_are_process_isolated_in_two_sandbox_workspaces(tmp_path):
    outputs = []
    for name, version in (("first", "1.0.0"), ("second", "2.0.0")):
        sandbox = tmp_path / name
        sandbox.mkdir()
        (sandbox / "shared_dependency.py").write_text(f"VERSION = {version!r}\n", encoding="utf-8")
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(sandbox)
        completed = subprocess.run(
            [sys.executable, "-c", "import shared_dependency; print(shared_dependency.VERSION)"],
            cwd=sandbox,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        outputs.append(completed.stdout.strip())

    assert outputs == ["1.0.0", "2.0.0"]


def test_project_dependency_input_does_not_inherit_optimizer_tool_pins(project_catalog):
    manifest = project_catalog["coverage_7_10_7"]["files"]["pyproject.toml"]

    # Pytest is intentionally project-declared at the same version as the
    # current optimizer.  Equality is not evidence of inheritance; the
    # project coverage constraint must remain its own 7.10.7 declaration and
    # unrelated optimizer packages must stay absent.
    assert "pytest==9.1.1" in manifest
    assert "coverage==7.10.7" in manifest
    assert "coverage==7.15.2" not in manifest
    assert "slipcover==1.0.18" not in manifest
    assert "pytest-repeat==0.9.4" not in manifest
    assert "pytest-timeout==2.4.0" not in manifest


def test_fingerprint_mismatch_is_rejected_before_scoring():
    run = RunSpec.from_dict(
        {
            "protocol_version": 1,
            "run_id": "phase1-candidate",
            "kind": "candidate",
            "environment_fingerprint": "a" * 64,
            "test_paths": ["generated_tests/test_candidate.py"],
        }
    )
    result = SandboxResult.from_dict(
        {
            "protocol_version": 1,
            "run_id": "phase1-candidate",
            "status": "succeeded",
            "environment_fingerprint": "b" * 64,
        }
    )

    with pytest.raises(ContractError, match="environment fingerprint"):
        require_matching_fingerprint(run, result)


@pytest.mark.parametrize(
    "output, expected_kind, retryable",
    [
        (
            "No solution found when resolving dependencies: requirements are unsatisfiable",
            ResolverErrorKind.DEPENDENCY_CONFLICT,
            False,
        ),
        ("HTTP 503 Service Unavailable while downloading wheel", ResolverErrorKind.NETWORK_TRANSIENT, True),
        ("Temporary failure in name resolution", ResolverErrorKind.NETWORK_TRANSIENT, True),
    ],
)
def test_network_failures_are_classified_differently_from_conflicts(output, expected_kind, retryable):
    diagnostic = classify_resolver_failure(output)

    assert diagnostic.kind == expected_kind
    assert diagnostic.retryable is retryable


@pytest.mark.xfail(
    strict=True,
    reason="Giai đoạn 4: production runtime must isolate coverage config before this regression can pass",
)
def test_project_fail_under_does_not_reject_runtime_admission(project_catalog, tmp_path):
    archive = write_case_zip(
        tmp_path / "fail-under-runtime.zip",
        project_catalog["coverage_fail_under"],
        "project",
    )

    result, python = prepare_environment(
        [RuntimeProjectSpec("fail-under", archive, "fail_under_pkg", "tests")],
        tmp_path / "fail-under-runtime",
        timeout_seconds=120,
    )

    assert result.status == "runtime_ready", result.error
    assert python is not None
