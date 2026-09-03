"""Feature-flagged migration between legacy runtime and project sandbox v2."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from .schemas import (
    FailureStage,
    ProjectRecord,
    RuntimeReport,
    RuntimeStatus,
)

_LOGGER = logging.getLogger("promptopt.runtime.rollout")
_TOKEN_PREFIX = "runtime-rollout-v1."


class RolloutMode(StrEnum):
    DISABLED = "disabled"
    SHADOW = "shadow"
    CANARY = "canary"
    ENABLED = "enabled"


class RuntimeRunner(Protocol):
    async def start(
        self,
        projects: list[ProjectRecord],
        *,
        reuse_bundle_object: str | None = None,
        expected_dependency_fingerprint: str | None = None,
    ) -> str: ...

    async def collect(self, prefix: str) -> RuntimeReport | None: ...


@dataclass(frozen=True, slots=True)
class RolloutPolicy:
    enabled: bool = False
    mode: RolloutMode = RolloutMode.DISABLED
    canary_percent: int = 0
    canary_python_versions: frozenset[str] = frozenset({"3.12"})

    def __post_init__(self) -> None:
        if not 0 <= self.canary_percent <= 100:
            raise ValueError("canary_percent must be between 0 and 100")

    def route(self, project: ProjectRecord) -> str:
        if not self.enabled or self.mode is RolloutMode.DISABLED:
            return "legacy"
        if self.mode is RolloutMode.SHADOW:
            return "shadow"
        if project.settings.runtime.python_version not in self.canary_python_versions:
            return "legacy"
        if self.mode is RolloutMode.ENABLED:
            return "sandbox"
        bucket = int.from_bytes(hashlib.sha256(project.id.encode()).digest()[:8], "big") % 100
        return "sandbox" if bucket < self.canary_percent else "legacy"


@dataclass(slots=True)
class RuntimeRolloutMetrics:
    starts: dict[str, int] = field(default_factory=dict)
    completions: dict[str, int] = field(default_factory=dict)
    failures: dict[str, int] = field(default_factory=dict)
    error_codes: dict[str, int] = field(default_factory=dict)
    protocol_versions: dict[str, int] = field(default_factory=dict)
    shadow_matches: int = 0
    shadow_mismatches: int = 0
    shadow_start_failures: int = 0
    rollback_routes: int = 0
    durations_seconds: list[float] = field(default_factory=list)

    @staticmethod
    def _increment(target: dict[str, int], key: str) -> None:
        target[key] = target.get(key, 0) + 1

    def started(self, route: str) -> None:
        self._increment(self.starts, route)
        if route == "legacy":
            self.rollback_routes += 1

    def completed(self, route: str, report: RuntimeReport, duration: float) -> None:
        self._increment(self.completions, route)
        self._increment(self.protocol_versions, str(report.protocol_version))
        self.durations_seconds.append(max(0.0, duration))
        if report.status is RuntimeStatus.FAILED:
            self._increment(self.failures, route)
            self._increment(self.error_codes, report.error_code or "UNKNOWN")

    def snapshot(self) -> dict[str, object]:
        durations = sorted(self.durations_seconds)

        def percentile(fraction: float) -> float | None:
            if not durations:
                return None
            return durations[min(len(durations) - 1, int((len(durations) - 1) * fraction))]

        return {
            "starts": dict(sorted(self.starts.items())),
            "completions": dict(sorted(self.completions.items())),
            "failures": dict(sorted(self.failures.items())),
            "error_codes": dict(sorted(self.error_codes.items())),
            "protocol_versions": dict(sorted(self.protocol_versions.items())),
            "shadow_matches": self.shadow_matches,
            "shadow_mismatches": self.shadow_mismatches,
            "shadow_start_failures": self.shadow_start_failures,
            "rollback_routes": self.rollback_routes,
            "duration_p50_seconds": percentile(0.50),
            "duration_p95_seconds": percentile(0.95),
        }


def parse_runtime_report(payload: dict[str, object]) -> RuntimeReport:
    """Dual-read legacy runtime reports and sandbox-result protocol v1."""

    if payload.get("status") not in {"succeeded", "failed"}:
        cleaned = dict(payload)
        cleaned.pop("project_root", None)
        projects = cleaned.get("projects")
        if isinstance(projects, dict):
            cleaned["projects"] = {
                key: {name: value for name, value in item.items() if name != "project_root"}
                if isinstance(item, dict)
                else item
                for key, item in projects.items()
            }
        return RuntimeReport.model_validate(cleaned)

    coverage = payload.get("coverage") if isinstance(payload.get("coverage"), dict) else {}

    def ratio(covered: str, total: str) -> float | None:
        denominator = int(coverage.get(total, 0))
        return int(coverage.get(covered, 0)) / denominator if denominator else None

    counts = payload.get("test_counts") if isinstance(payload.get("test_counts"), dict) else {}
    stage = payload.get("failure_stage")
    failure_stage = FailureStage.TEST if stage == "timeout" else None
    if stage in {item.value for item in FailureStage}:
        failure_stage = FailureStage(str(stage))
    return RuntimeReport(
        status=RuntimeStatus.READY if payload["status"] == "succeeded" else RuntimeStatus.FAILED,
        collected_tests=int(counts.get("collected", 0)),
        statement_coverage=ratio("covered_statements", "total_statements"),
        branch_coverage=ratio("covered_branches", "total_branches"),
        error=(payload.get("stderr") or payload.get("stdout") or None),
        failure_stage=failure_stage,
        error_code=str(payload["error_code"]) if payload.get("error_code") else None,
        retryable=bool(payload.get("retryable", False)),
        environment_fingerprint=(
            str(payload["environment_fingerprint"]) if payload.get("environment_fingerprint") else None
        ),
        runner_profile=str(payload["runner_profile"]) if payload.get("runner_profile") else None,
        pytest_version=str(payload["pytest_version"]) if payload.get("pytest_version") else None,
        coverage_version=str(payload["coverage_version"]) if payload.get("coverage_version") else None,
        protocol_version=int(payload.get("protocol_version", 1)),
    )


def _encode_token(payload: dict[str, object]) -> str:
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).decode()
    return _TOKEN_PREFIX + encoded.rstrip("=")


def _decode_token(token: str) -> dict[str, object]:
    if not token.startswith(_TOKEN_PREFIX):
        raise ValueError("Invalid rollout execution token")
    encoded = token.removeprefix(_TOKEN_PREFIX)
    return json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))


class RuntimeRolloutPreparer:
    """Route runtime admission while preserving legacy activation and rollback."""

    def __init__(
        self,
        legacy: RuntimeRunner,
        sandbox: RuntimeRunner | None,
        policy: RolloutPolicy,
        *,
        metrics: RuntimeRolloutMetrics | None = None,
        advertised_python_versions: frozenset[str] = frozenset(),
        clock=time.time,
    ) -> None:
        self.legacy = legacy
        self.sandbox = sandbox
        self.policy = policy
        self.metrics = metrics or RuntimeRolloutMetrics()
        self.advertised_python_versions = advertised_python_versions
        self.clock = clock

    @property
    def image(self) -> str:
        selected = self.sandbox if self.advertised_python_versions and self.sandbox else self.legacy
        return getattr(selected, "image", "promptopt-sandbox:py3.12")

    @property
    def job_name(self) -> str:
        selected = self.sandbox if self.advertised_python_versions and self.sandbox else self.legacy
        return getattr(selected, "job_name", "promptopt-runtime-preparer")

    def is_healthy(self) -> bool:
        legacy_health = getattr(self.legacy, "is_healthy", lambda: True)()
        if not self.policy.enabled or self.policy.mode is RolloutMode.DISABLED:
            return bool(legacy_health)
        sandbox_health = bool(self.sandbox and getattr(self.sandbox, "is_healthy", lambda: True)())
        return bool(legacy_health and sandbox_health)

    async def start(
        self,
        projects: list[ProjectRecord],
        *,
        reuse_bundle_object: str | None = None,
        expected_dependency_fingerprint: str | None = None,
    ) -> str:
        if not projects:
            raise ValueError("Runtime rollout requires at least one project")
        route = self.policy.route(projects[-1])
        options = {
            "reuse_bundle_object": reuse_bundle_object,
            "expected_dependency_fingerprint": expected_dependency_fingerprint,
        }
        started_at = self.clock()
        self.metrics.started(route)
        if route == "legacy":
            prefix = await self.legacy.start(projects, **options)
            return _encode_token({"route": route, "legacy": prefix, "started_at": started_at})
        if self.sandbox is None:
            raise RuntimeError("Project sandbox v2 is selected but no sandbox runner is configured")
        if route == "sandbox":
            prefix = await self.sandbox.start(projects, **options)
            return _encode_token({"route": route, "sandbox": prefix, "started_at": started_at})

        legacy_prefix = await self.legacy.start(projects, **options)
        sandbox_prefix = None
        try:
            sandbox_prefix = await self.sandbox.start(projects, **options)
        except Exception as exc:  # shadow failure must never block legacy activation
            self.metrics.shadow_start_failures += 1
            _LOGGER.warning(
                "runtime_rollout shadow_start_failed project_id=%s error_type=%s",
                projects[-1].id,
                type(exc).__name__,
            )
        return _encode_token(
            {
                "route": route,
                "legacy": legacy_prefix,
                "sandbox": sandbox_prefix,
                "started_at": started_at,
            }
        )

    async def collect(self, token: str) -> RuntimeReport | None:
        state = _decode_token(token)
        route = str(state["route"])
        started_at = float(state["started_at"])
        if route == "legacy":
            report = await self.legacy.collect(str(state["legacy"]))
        elif route == "sandbox":
            if self.sandbox is None:
                raise RuntimeError("Project sandbox v2 runner disappeared during execution")
            report = await self.sandbox.collect(str(state["sandbox"]))
        else:
            legacy_report = await self.legacy.collect(str(state["legacy"]))
            sandbox_prefix = state.get("sandbox")
            sandbox_report = (
                await self.sandbox.collect(str(sandbox_prefix))
                if self.sandbox is not None and sandbox_prefix
                else None
            )
            if legacy_report is None or (sandbox_prefix and sandbox_report is None):
                return None
            self._compare_shadow(legacy_report, sandbox_report)
            report = legacy_report
        if report is not None:
            self.metrics.completed(route, report, self.clock() - started_at)
            _LOGGER.info(
                "runtime_rollout completed route=%s status=%s protocol=%s",
                route,
                report.status.value,
                report.protocol_version,
            )
        return report

    def _compare_shadow(self, legacy: RuntimeReport, sandbox: RuntimeReport | None) -> None:
        comparable = sandbox is not None and (
            legacy.status,
            legacy.collected_tests,
            legacy.error_code,
        ) == (
            sandbox.status,
            sandbox.collected_tests,
            sandbox.error_code,
        )
        if comparable:
            self.metrics.shadow_matches += 1
        else:
            self.metrics.shadow_mismatches += 1
        _LOGGER.info(
            "runtime_rollout shadow_comparison match=%s legacy_status=%s sandbox_status=%s",
            comparable,
            legacy.status.value,
            sandbox.status.value if sandbox else "unavailable",
        )
