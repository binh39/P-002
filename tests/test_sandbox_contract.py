import json
from pathlib import Path

import pytest

from cloud.sandbox_contract import (
    ContractError,
    RunKind,
    RunnerProfile,
    RunSpec,
    SandboxResult,
    SandboxSpec,
    SandboxStatus,
    require_matching_fingerprint,
)

EXAMPLES = Path(__file__).parents[1] / "docs" / "contracts" / "examples"


def load_example(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def test_sandbox_spec_example_round_trips():
    payload = load_example("sandbox_spec.v1.json")

    spec = SandboxSpec.from_dict(payload)

    assert spec.project_id == "isort"
    assert spec.runner_profile == RunnerProfile.PROJECT_NATIVE
    assert spec.dependency_policy.lock_file == "uv.lock"
    assert spec.as_dict() == payload


def test_baseline_and_candidate_run_specs_share_environment_fingerprint():
    baseline = RunSpec.from_dict(load_example("run_spec.baseline.v1.json"))
    candidate = RunSpec.from_dict(load_example("run_spec.candidate.v1.json"))

    assert baseline.kind == RunKind.BASELINE
    assert candidate.kind == RunKind.CANDIDATE
    assert baseline.environment_fingerprint == candidate.environment_fingerprint
    assert baseline.as_dict() == load_example("run_spec.baseline.v1.json")
    assert candidate.as_dict() == load_example("run_spec.candidate.v1.json")


@pytest.mark.parametrize(
    "filename, expected_status",
    [
        ("sandbox_result.success.v1.json", SandboxStatus.SUCCEEDED),
        ("sandbox_result.failure.v1.json", SandboxStatus.FAILED),
    ],
)
def test_sandbox_result_examples_round_trip(filename, expected_status):
    payload = load_example(filename)

    result = SandboxResult.from_dict(payload)

    assert result.status == expected_status
    assert result.as_dict() == payload


def test_result_optional_fields_are_backward_compatible():
    result = SandboxResult.from_dict(
        {
            "protocol_version": 1,
            "run_id": "minimal-result",
            "status": "succeeded",
            "environment_fingerprint": "b" * 64,
        }
    )

    assert result.exit_code is None
    assert result.coverage is None
    assert result.test_counts.collected == 0


def test_run_spec_accepts_bounded_source_symbol_identity():
    payload = load_example("run_spec.candidate.v1.json")
    payload.update({"source_file": "isort/settings.py", "symbol": "Config.from_path"})

    run = RunSpec.from_dict(payload)

    assert run.source_file == "isort/settings.py"
    assert run.symbol == "Config.from_path"
    assert run.as_dict() == payload


def test_run_spec_requires_source_file_and_symbol_together():
    payload = load_example("run_spec.candidate.v1.json")
    payload["source_file"] = "isort/settings.py"

    with pytest.raises(ContractError, match="provided together"):
        RunSpec.from_dict(payload)


def test_result_can_report_actual_runner_identity():
    payload = load_example("sandbox_result.success.v1.json")
    payload.update(
        {
            "runner_profile": "project_native",
            "pytest_version": "8.4.2",
            "coverage_version": "7.10.7",
        }
    )

    result = SandboxResult.from_dict(payload)

    assert result.runner_profile == RunnerProfile.PROJECT_NATIVE
    assert result.as_dict() == payload


def test_contract_rejects_unknown_fields():
    payload = load_example("sandbox_spec.v1.json")
    payload["install_command"] = "pip install anything"

    with pytest.raises(ContractError, match="unknown fields: install_command"):
        SandboxSpec.from_dict(payload)


@pytest.mark.parametrize("path", ["../host", "/etc/passwd", "tests/../../host"])
def test_contract_rejects_paths_outside_workspace(path):
    payload = load_example("sandbox_spec.v1.json")
    payload["source_directory"] = path

    with pytest.raises(ContractError, match="inside the project workspace"):
        SandboxSpec.from_dict(payload)


def test_contract_rejects_arbitrary_test_pattern_path():
    payload = load_example("run_spec.baseline.v1.json")
    payload["test_pattern"] = "../../*.py"

    with pytest.raises(ContractError, match="filename pattern"):
        RunSpec.from_dict(payload)


def test_contract_rejects_environment_assignments_and_secret_values():
    payload = load_example("sandbox_spec.v1.json")
    payload["allowed_environment_variables"] = ["TOKEN=secret"]

    with pytest.raises(ContractError, match="invalid environment variable name"):
        SandboxSpec.from_dict(payload)


def test_locked_dependency_policy_requires_a_lock_file():
    payload = load_example("sandbox_spec.v1.json")
    payload["dependency_policy"].pop("lock_file")

    with pytest.raises(ContractError, match="lock_file is required"):
        SandboxSpec.from_dict(payload)


def test_failed_result_requires_structured_diagnostics():
    payload = load_example("sandbox_result.failure.v1.json")
    payload.pop("error_code")

    with pytest.raises(ContractError, match="requires failure_stage and error_code"):
        SandboxResult.from_dict(payload)


def test_successful_result_rejects_failure_diagnostics():
    payload = load_example("sandbox_result.success.v1.json")
    payload["failure_stage"] = "internal"
    payload["error_code"] = "SHOULD_NOT_EXIST"

    with pytest.raises(ContractError, match="successful sandbox result"):
        SandboxResult.from_dict(payload)


def test_scoring_gate_accepts_matching_run_and_fingerprint():
    run = RunSpec.from_dict(load_example("run_spec.candidate.v1.json"))
    result = SandboxResult.from_dict(load_example("sandbox_result.success.v1.json"))

    require_matching_fingerprint(run, result)


def test_scoring_gate_rejects_fingerprint_mismatch():
    run = RunSpec.from_dict(load_example("run_spec.candidate.v1.json"))
    payload = load_example("sandbox_result.success.v1.json")
    payload["environment_fingerprint"] = "c" * 64
    result = SandboxResult.from_dict(payload)

    with pytest.raises(ContractError, match="environment fingerprint"):
        require_matching_fingerprint(run, result)


def test_scoring_gate_rejects_run_id_mismatch():
    run = RunSpec.from_dict(load_example("run_spec.candidate.v1.json"))
    payload = load_example("sandbox_result.success.v1.json")
    payload["run_id"] = "another-run"
    result = SandboxResult.from_dict(payload)

    with pytest.raises(ContractError, match="run_id"):
        require_matching_fingerprint(run, result)
