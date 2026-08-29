"""Runner-profile selection policy validated by the Phase 0 spike.

The selector is dependency free and does not install or mutate packages.  It
turns an already-resolved project inventory into an explicit runner decision.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from cloud.sandbox_contract import RunnerProfile

PROJECT_NATIVE_PYTEST_MAJORS = frozenset({7, 8, 9})
PROJECT_NATIVE_COVERAGE_MAJORS = frozenset({7})
SANDBOX_MANAGED_PYTEST = "9.1.1"
SANDBOX_MANAGED_COVERAGE = "7.15.3"


@dataclass(frozen=True, slots=True)
class RunnerDecision:
    profile: RunnerProfile
    pytest_version: str | None
    coverage_version: str | None
    reason: str
    error_code: str | None = None


def _major(version: str) -> int | None:
    match = re.match(r"^(\d+)(?:\.|$)", version)
    return int(match.group(1)) if match else None


def select_runner_profile(packages: Mapping[str, str]) -> RunnerDecision:
    """Select a runner without changing the project's package inventory.

    Package names must already be normalized to lowercase with ``-`` as their
    separator.  A partial or unsupported native toolchain is rejected instead
    of being silently upgraded/downgraded.
    """

    normalized = {name.lower().replace("_", "-"): version for name, version in packages.items()}
    pytest_version = normalized.get("pytest")
    coverage_version = normalized.get("coverage")

    if pytest_version is None and coverage_version is None:
        return RunnerDecision(
            profile=RunnerProfile.SANDBOX_MANAGED,
            pytest_version=SANDBOX_MANAGED_PYTEST,
            coverage_version=SANDBOX_MANAGED_COVERAGE,
            reason="Project does not declare pytest or coverage; use the isolated sandbox runner layer",
        )

    if pytest_version is None or coverage_version is None:
        missing = "pytest" if pytest_version is None else "coverage"
        return RunnerDecision(
            profile=RunnerProfile.COMPATIBILITY_FALLBACK,
            pytest_version=pytest_version,
            coverage_version=coverage_version,
            reason=f"Project-native test tooling is incomplete: missing {missing}",
            error_code="INCOMPLETE_PROJECT_RUNNER",
        )

    pytest_major = _major(pytest_version)
    coverage_major = _major(coverage_version)
    if pytest_major not in PROJECT_NATIVE_PYTEST_MAJORS or coverage_major not in PROJECT_NATIVE_COVERAGE_MAJORS:
        return RunnerDecision(
            profile=RunnerProfile.COMPATIBILITY_FALLBACK,
            pytest_version=pytest_version,
            coverage_version=coverage_version,
            reason="Project-native pytest/coverage versions are outside the validated compatibility matrix",
            error_code="UNSUPPORTED_PROJECT_RUNNER",
        )

    return RunnerDecision(
        profile=RunnerProfile.PROJECT_NATIVE,
        pytest_version=pytest_version,
        coverage_version=coverage_version,
        reason="Use the compatible pytest and coverage versions already resolved by the project",
    )
