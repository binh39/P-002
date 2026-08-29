"""Versioned, dependency-free contracts for project sandbox evaluation.

This module intentionally uses only the Python standard library.  Importing a
sandbox request or result must never pull optimizer dependencies into a project
environment.  The contracts are not wired into the production runtime yet;
they define and validate the protocol selected in Phase 0 of the migration.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from pathlib import PurePosixPath
from typing import Any

SANDBOX_PROTOCOL_VERSION = 1
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_PYTHON_PATTERN = re.compile(r"^3\.(10|11|12|13)$")
_ENVIRONMENT_NAME_PATTERN = re.compile(r"^[A-Z_][A-Z0-9_]*$")
_SYMBOL_PATTERN = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*$")


class ContractError(ValueError):
    """Raised when a sandbox protocol payload violates its schema."""


class StringEnum(str, Enum):  # noqa: UP042 - sandbox contract supports Python 3.10
    """A Python 3.10-compatible string enum."""


class DependencyMode(StringEnum):
    LOCKED = "locked"
    MANIFEST = "manifest"
    NONE = "none"


class RunnerProfile(StringEnum):
    PROJECT_NATIVE = "project_native"
    SANDBOX_MANAGED = "sandbox_managed"
    COMPATIBILITY_FALLBACK = "compatibility_fallback"


class CoverageMode(StringEnum):
    STATEMENT = "statement"
    STATEMENT_AND_BRANCH = "statement_and_branch"


class RunKind(StringEnum):
    BASELINE = "baseline"
    CANDIDATE = "candidate"


class SandboxStatus(StringEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class FailureStage(StringEnum):
    BUILD = "build"
    COLLECT = "collect"
    TEST = "test"
    COVERAGE = "coverage"
    TIMEOUT = "timeout"
    INTERNAL = "internal"


def _strict_mapping(
    value: Any,
    *,
    name: str,
    required: set[str],
    optional: set[str] | None = None,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{name} must be an object")
    optional = optional or set()
    missing = required - set(value)
    extra = set(value) - required - optional
    if missing:
        raise ContractError(f"{name} is missing fields: {', '.join(sorted(missing))}")
    if extra:
        raise ContractError(f"{name} contains unknown fields: {', '.join(sorted(extra))}")
    return value


def _string(value: Any, *, name: str, minimum: int = 1, maximum: int = 500) -> str:
    if not isinstance(value, str) or not minimum <= len(value) <= maximum:
        raise ContractError(f"{name} must be a string with length {minimum}..{maximum}")
    return value


def _integer(value: Any, *, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ContractError(f"{name} must be an integer in range {minimum}..{maximum}")
    return value


def _number(value: Any, *, name: str, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or float(value) < minimum:
        raise ContractError(f"{name} must be a number greater than or equal to {minimum}")
    return float(value)


def _enum(enum_type: type[StringEnum], value: Any, *, name: str) -> StringEnum:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        choices = ", ".join(item.value for item in enum_type)
        raise ContractError(f"{name} must be one of: {choices}") from exc


def _relative_path(value: Any, *, name: str) -> str:
    path = _string(value, name=name, maximum=300).replace("\\", "/")
    parsed = PurePosixPath(path)
    if parsed.is_absolute() or ".." in parsed.parts or path.startswith("//"):
        raise ContractError(f"{name} must stay inside the project workspace")
    return parsed.as_posix()


def _sha256(value: Any, *, name: str) -> str:
    text = _string(value, name=name, minimum=64, maximum=64)
    if not _SHA256_PATTERN.fullmatch(text):
        raise ContractError(f"{name} must be a lowercase SHA-256 digest")
    return text


def _python_version(value: Any, *, name: str) -> str:
    text = _string(value, name=name, maximum=4)
    if not _PYTHON_PATTERN.fullmatch(text):
        raise ContractError(f"{name} must be one of Python 3.10, 3.11, 3.12 or 3.13")
    return text


def _string_list(value: Any, *, name: str, maximum_items: int = 100) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > maximum_items:
        raise ContractError(f"{name} must be an array with at most {maximum_items} items")
    return tuple(_string(item, name=f"{name}[]") for item in value)


@dataclass(frozen=True, slots=True)
class ResourceLimits:
    cpu: int = 1
    memory_mb: int = 2048
    timeout_seconds: int = 900
    maximum_processes: int = 128
    maximum_output_bytes: int = 10 * 1024 * 1024
    maximum_file_bytes: int = 100 * 1024 * 1024

    @classmethod
    def from_dict(cls, raw: Any) -> ResourceLimits:
        data = _strict_mapping(
            raw,
            name="resource_limits",
            required={"cpu", "memory_mb", "timeout_seconds", "maximum_processes", "maximum_output_bytes"},
            optional={"maximum_file_bytes"},
        )
        return cls(
            cpu=_integer(data["cpu"], name="resource_limits.cpu", minimum=1, maximum=8),
            memory_mb=_integer(data["memory_mb"], name="resource_limits.memory_mb", minimum=512, maximum=32768),
            timeout_seconds=_integer(
                data["timeout_seconds"], name="resource_limits.timeout_seconds", minimum=30, maximum=7200
            ),
            maximum_processes=_integer(
                data["maximum_processes"], name="resource_limits.maximum_processes", minimum=1, maximum=1024
            ),
            maximum_output_bytes=_integer(
                data["maximum_output_bytes"],
                name="resource_limits.maximum_output_bytes",
                minimum=1024,
                maximum=100 * 1024 * 1024,
            ),
            maximum_file_bytes=_integer(
                data.get("maximum_file_bytes", 100 * 1024 * 1024),
                name="resource_limits.maximum_file_bytes",
                minimum=1024 * 1024,
                maximum=1024 * 1024 * 1024,
            ),
        )

    def as_dict(self) -> dict[str, int]:
        return {
            "cpu": self.cpu,
            "memory_mb": self.memory_mb,
            "timeout_seconds": self.timeout_seconds,
            "maximum_processes": self.maximum_processes,
            "maximum_output_bytes": self.maximum_output_bytes,
            "maximum_file_bytes": self.maximum_file_bytes,
        }


@dataclass(frozen=True, slots=True)
class DependencyPolicy:
    mode: DependencyMode
    manifest: str | None = None
    lock_file: str | None = None
    groups: tuple[str, ...] = ()
    extras: tuple[str, ...] = ()
    package_index_refs: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, raw: Any) -> DependencyPolicy:
        data = _strict_mapping(
            raw,
            name="dependency_policy",
            required={"mode", "groups", "extras", "package_index_refs"},
            optional={"manifest", "lock_file"},
        )
        mode = _enum(DependencyMode, data["mode"], name="dependency_policy.mode")
        manifest = (
            _relative_path(data["manifest"], name="dependency_policy.manifest")
            if data.get("manifest") is not None
            else None
        )
        lock_file = (
            _relative_path(data["lock_file"], name="dependency_policy.lock_file")
            if data.get("lock_file") is not None
            else None
        )
        if mode == DependencyMode.LOCKED and not lock_file:
            raise ContractError("dependency_policy.lock_file is required for locked mode")
        if mode == DependencyMode.MANIFEST and not manifest:
            raise ContractError("dependency_policy.manifest is required for manifest mode")
        if mode == DependencyMode.NONE and (manifest or lock_file):
            raise ContractError("dependency_policy none mode cannot declare a manifest or lock file")
        groups = _string_list(data["groups"], name="dependency_policy.groups", maximum_items=30)
        extras = _string_list(data["extras"], name="dependency_policy.extras", maximum_items=30)
        index_refs = _string_list(
            data["package_index_refs"], name="dependency_policy.package_index_refs", maximum_items=10
        )
        for collection_name, values in (("groups", groups), ("extras", extras), ("package_index_refs", index_refs)):
            if len(set(values)) != len(values):
                raise ContractError(f"dependency_policy.{collection_name} cannot contain duplicates")
        return cls(mode, manifest, lock_file, groups, extras, index_refs)

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "manifest": self.manifest,
            "lock_file": self.lock_file,
            "groups": list(self.groups),
            "extras": list(self.extras),
            "package_index_refs": list(self.package_index_refs),
        }


@dataclass(frozen=True, slots=True)
class SandboxSpec:
    project_id: str
    archive_sha256: str
    requested_python: str
    detected_python: str | None
    source_directory: str
    test_directory: str
    dependency_policy: DependencyPolicy
    runner_profile: RunnerProfile
    coverage_mode: CoverageMode
    allowed_environment_variables: tuple[str, ...]
    resource_limits: ResourceLimits
    protocol_version: int = SANDBOX_PROTOCOL_VERSION

    @classmethod
    def from_dict(cls, raw: Any) -> SandboxSpec:
        data = _strict_mapping(
            raw,
            name="sandbox_spec",
            required={
                "protocol_version",
                "project_id",
                "archive_sha256",
                "requested_python",
                "source_directory",
                "test_directory",
                "dependency_policy",
                "runner_profile",
                "coverage_mode",
                "allowed_environment_variables",
                "resource_limits",
            },
            optional={"detected_python"},
        )
        protocol_version = _integer(
            data["protocol_version"], name="sandbox_spec.protocol_version", minimum=1, maximum=1
        )
        environment = _string_list(
            data["allowed_environment_variables"],
            name="sandbox_spec.allowed_environment_variables",
            maximum_items=30,
        )
        for item in environment:
            if not _ENVIRONMENT_NAME_PATTERN.fullmatch(item):
                raise ContractError(f"invalid environment variable name: {item}")
        if len(set(environment)) != len(environment):
            raise ContractError("allowed_environment_variables cannot contain duplicates")
        detected = data.get("detected_python")
        return cls(
            project_id=_string(data["project_id"], name="sandbox_spec.project_id", maximum=100),
            archive_sha256=_sha256(data["archive_sha256"], name="sandbox_spec.archive_sha256"),
            requested_python=_python_version(data["requested_python"], name="sandbox_spec.requested_python"),
            detected_python=(
                _python_version(detected, name="sandbox_spec.detected_python") if detected is not None else None
            ),
            source_directory=_relative_path(data["source_directory"], name="sandbox_spec.source_directory"),
            test_directory=_relative_path(data["test_directory"], name="sandbox_spec.test_directory"),
            dependency_policy=DependencyPolicy.from_dict(data["dependency_policy"]),
            runner_profile=_enum(RunnerProfile, data["runner_profile"], name="sandbox_spec.runner_profile"),
            coverage_mode=_enum(CoverageMode, data["coverage_mode"], name="sandbox_spec.coverage_mode"),
            allowed_environment_variables=environment,
            resource_limits=ResourceLimits.from_dict(data["resource_limits"]),
            protocol_version=protocol_version,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "protocol_version": self.protocol_version,
            "project_id": self.project_id,
            "archive_sha256": self.archive_sha256,
            "requested_python": self.requested_python,
            "detected_python": self.detected_python,
            "source_directory": self.source_directory,
            "test_directory": self.test_directory,
            "dependency_policy": self.dependency_policy.as_dict(),
            "runner_profile": self.runner_profile.value,
            "coverage_mode": self.coverage_mode.value,
            "allowed_environment_variables": list(self.allowed_environment_variables),
            "resource_limits": self.resource_limits.as_dict(),
        }


@dataclass(frozen=True, slots=True)
class RunSpec:
    run_id: str
    kind: RunKind
    environment_fingerprint: str
    test_paths: tuple[str, ...]
    test_pattern: str = "test_*.py"
    source_file: str | None = None
    symbol: str | None = None
    protocol_version: int = SANDBOX_PROTOCOL_VERSION

    @classmethod
    def from_dict(cls, raw: Any) -> RunSpec:
        data = _strict_mapping(
            raw,
            name="run_spec",
            required={"protocol_version", "run_id", "kind", "environment_fingerprint", "test_paths"},
            optional={"test_pattern", "source_file", "symbol"},
        )
        protocol_version = _integer(data["protocol_version"], name="run_spec.protocol_version", minimum=1, maximum=1)
        raw_paths = _string_list(data["test_paths"], name="run_spec.test_paths", maximum_items=1000)
        if not raw_paths:
            raise ContractError("run_spec.test_paths cannot be empty")
        paths = tuple(_relative_path(item, name="run_spec.test_paths[]") for item in raw_paths)
        pattern = _string(data.get("test_pattern", "test_*.py"), name="run_spec.test_pattern", maximum=100)
        if "/" in pattern or "\\" in pattern or ".." in pattern:
            raise ContractError("run_spec.test_pattern must be a filename pattern, not a path")
        source_file = data.get("source_file")
        if source_file is not None:
            source_file = _relative_path(source_file, name="run_spec.source_file")
            if not source_file.endswith(".py"):
                raise ContractError("run_spec.source_file must identify a Python source file")
        symbol = data.get("symbol")
        if symbol is not None:
            symbol = _string(symbol, name="run_spec.symbol", maximum=300)
            if not _SYMBOL_PATTERN.fullmatch(symbol):
                raise ContractError("run_spec.symbol must be a dotted Python qualname")
        if (source_file is None) != (symbol is None):
            raise ContractError("run_spec.source_file and run_spec.symbol must be provided together")
        return cls(
            run_id=_string(data["run_id"], name="run_spec.run_id", maximum=100),
            kind=_enum(RunKind, data["kind"], name="run_spec.kind"),
            environment_fingerprint=_sha256(data["environment_fingerprint"], name="run_spec.environment_fingerprint"),
            test_paths=paths,
            test_pattern=pattern,
            source_file=source_file,
            symbol=symbol,
            protocol_version=protocol_version,
        )

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "protocol_version": self.protocol_version,
            "run_id": self.run_id,
            "kind": self.kind.value,
            "environment_fingerprint": self.environment_fingerprint,
            "test_paths": list(self.test_paths),
            "test_pattern": self.test_pattern,
        }
        if self.source_file is not None:
            payload["source_file"] = self.source_file
            payload["symbol"] = self.symbol
        return payload


@dataclass(frozen=True, slots=True)
class TestCounts:
    collected: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0

    @classmethod
    def from_dict(cls, raw: Any) -> TestCounts:
        data = _strict_mapping(raw, name="test_counts", required={"collected", "passed", "failed", "skipped"})
        values = {
            key: _integer(data[key], name=f"test_counts.{key}", minimum=0, maximum=10_000_000)
            for key in ("collected", "passed", "failed", "skipped")
        }
        if values["passed"] + values["failed"] + values["skipped"] > values["collected"]:
            raise ContractError("test count outcomes cannot exceed collected tests")
        return cls(**values)

    def as_dict(self) -> dict[str, int]:
        return {
            "collected": self.collected,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
        }


@dataclass(frozen=True, slots=True)
class CoverageSummary:
    covered_statements: int
    total_statements: int
    covered_branches: int
    total_branches: int

    @classmethod
    def from_dict(cls, raw: Any) -> CoverageSummary:
        data = _strict_mapping(
            raw,
            name="coverage_summary",
            required={"covered_statements", "total_statements", "covered_branches", "total_branches"},
        )
        values = {
            key: _integer(data[key], name=f"coverage_summary.{key}", minimum=0, maximum=1_000_000_000)
            for key in ("covered_statements", "total_statements", "covered_branches", "total_branches")
        }
        if values["covered_statements"] > values["total_statements"]:
            raise ContractError("covered_statements cannot exceed total_statements")
        if values["covered_branches"] > values["total_branches"]:
            raise ContractError("covered_branches cannot exceed total_branches")
        return cls(**values)

    def as_dict(self) -> dict[str, int]:
        return {
            "covered_statements": self.covered_statements,
            "total_statements": self.total_statements,
            "covered_branches": self.covered_branches,
            "total_branches": self.total_branches,
        }


@dataclass(frozen=True, slots=True)
class SandboxResult:
    run_id: str
    status: SandboxStatus
    environment_fingerprint: str
    exit_code: int | None = None
    failure_stage: FailureStage | None = None
    error_code: str | None = None
    retryable: bool = False
    test_counts: TestCounts = field(default_factory=TestCounts)
    coverage: CoverageSummary | None = None
    coverage_artifact: str | None = None
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0
    peak_memory_mb: float | None = None
    runner_profile: RunnerProfile | None = None
    pytest_version: str | None = None
    coverage_version: str | None = None
    protocol_version: int = SANDBOX_PROTOCOL_VERSION

    @classmethod
    def from_dict(cls, raw: Any) -> SandboxResult:
        data = _strict_mapping(
            raw,
            name="sandbox_result",
            required={"protocol_version", "run_id", "status", "environment_fingerprint"},
            optional={
                "exit_code",
                "failure_stage",
                "error_code",
                "retryable",
                "test_counts",
                "coverage",
                "coverage_artifact",
                "stdout",
                "stderr",
                "duration_seconds",
                "peak_memory_mb",
                "runner_profile",
                "pytest_version",
                "coverage_version",
            },
        )
        protocol_version = _integer(
            data["protocol_version"], name="sandbox_result.protocol_version", minimum=1, maximum=1
        )
        status = _enum(SandboxStatus, data["status"], name="sandbox_result.status")
        exit_code = data.get("exit_code")
        if exit_code is not None:
            exit_code = _integer(exit_code, name="sandbox_result.exit_code", minimum=-1, maximum=255)
        failure_raw = data.get("failure_stage")
        failure_stage = (
            _enum(FailureStage, failure_raw, name="sandbox_result.failure_stage") if failure_raw is not None else None
        )
        error_code = data.get("error_code")
        if error_code is not None:
            error_code = _string(error_code, name="sandbox_result.error_code", maximum=100)
        retryable = data.get("retryable", False)
        if not isinstance(retryable, bool):
            raise ContractError("sandbox_result.retryable must be a boolean")
        if status == SandboxStatus.SUCCEEDED and (failure_stage or error_code or retryable):
            raise ContractError("a successful sandbox result cannot contain failure diagnostics")
        if status == SandboxStatus.FAILED and (not failure_stage or not error_code):
            raise ContractError("a failed sandbox result requires failure_stage and error_code")
        coverage_artifact = data.get("coverage_artifact")
        if coverage_artifact is not None:
            coverage_artifact = _relative_path(coverage_artifact, name="sandbox_result.coverage_artifact")
        peak_memory = data.get("peak_memory_mb")
        runner_raw = data.get("runner_profile")
        runner_profile = _enum(RunnerProfile, runner_raw, name="sandbox_result.runner_profile") if runner_raw else None
        pytest_version = data.get("pytest_version")
        coverage_version = data.get("coverage_version")
        if pytest_version is not None:
            pytest_version = _string(pytest_version, name="sandbox_result.pytest_version", maximum=100)
        if coverage_version is not None:
            coverage_version = _string(coverage_version, name="sandbox_result.coverage_version", maximum=100)
        if runner_profile is None and (pytest_version is not None or coverage_version is not None):
            raise ContractError("sandbox_result runner versions require runner_profile")
        return cls(
            run_id=_string(data["run_id"], name="sandbox_result.run_id", maximum=100),
            status=status,
            environment_fingerprint=_sha256(
                data["environment_fingerprint"], name="sandbox_result.environment_fingerprint"
            ),
            exit_code=exit_code,
            failure_stage=failure_stage,
            error_code=error_code,
            retryable=retryable,
            test_counts=TestCounts.from_dict(data.get("test_counts", TestCounts().as_dict())),
            coverage=CoverageSummary.from_dict(data["coverage"]) if data.get("coverage") is not None else None,
            coverage_artifact=coverage_artifact,
            stdout=_string(data.get("stdout", ""), name="sandbox_result.stdout", minimum=0, maximum=10 * 1024 * 1024),
            stderr=_string(data.get("stderr", ""), name="sandbox_result.stderr", minimum=0, maximum=10 * 1024 * 1024),
            duration_seconds=_number(data.get("duration_seconds", 0.0), name="sandbox_result.duration_seconds"),
            peak_memory_mb=(
                _number(peak_memory, name="sandbox_result.peak_memory_mb") if peak_memory is not None else None
            ),
            runner_profile=runner_profile,
            pytest_version=pytest_version,
            coverage_version=coverage_version,
            protocol_version=protocol_version,
        )

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "protocol_version": self.protocol_version,
            "run_id": self.run_id,
            "status": self.status.value,
            "environment_fingerprint": self.environment_fingerprint,
            "exit_code": self.exit_code,
            "failure_stage": self.failure_stage.value if self.failure_stage else None,
            "error_code": self.error_code,
            "retryable": self.retryable,
            "test_counts": self.test_counts.as_dict(),
            "coverage": self.coverage.as_dict() if self.coverage else None,
            "coverage_artifact": self.coverage_artifact,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_seconds": self.duration_seconds,
            "peak_memory_mb": self.peak_memory_mb,
        }
        if self.runner_profile is not None:
            payload["runner_profile"] = self.runner_profile.value
            payload["pytest_version"] = self.pytest_version
            payload["coverage_version"] = self.coverage_version
        return payload


def require_matching_fingerprint(run_spec: RunSpec, result: SandboxResult) -> None:
    """Reject scoring inputs produced by a different project environment."""

    if run_spec.run_id != result.run_id:
        raise ContractError("sandbox result run_id does not match the run specification")
    if run_spec.environment_fingerprint != result.environment_fingerprint:
        raise ContractError("sandbox result environment fingerprint does not match the run specification")
