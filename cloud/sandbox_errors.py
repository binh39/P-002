"""Dependency-free resolver failure classification for sandbox contracts.

The classifier is intentionally not wired into the v8 production runtime yet.
It provides deterministic error semantics for Phase 1 regression tests and the
future sandbox builder.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ResolverErrorKind(str, Enum):  # noqa: UP042 - contract must support Python 3.10
    DEPENDENCY_CONFLICT = "dependency_conflict"
    PACKAGE_NOT_FOUND = "package_not_found"
    INCOMPATIBLE_PYTHON = "incompatible_python"
    INDEX_AUTH = "index_auth"
    NETWORK_TRANSIENT = "network_transient"
    TIMEOUT = "timeout"
    INTERNAL = "internal"


@dataclass(frozen=True, slots=True)
class ResolverDiagnostic:
    kind: ResolverErrorKind
    error_code: str
    retryable: bool


_PATTERNS: tuple[tuple[ResolverErrorKind, tuple[str, ...], str, bool], ...] = (
    (
        ResolverErrorKind.INCOMPATIBLE_PYTHON,
        ("requires python", "python requirement", "unsupported python"),
        "INCOMPATIBLE_PYTHON",
        False,
    ),
    (
        ResolverErrorKind.INDEX_AUTH,
        ("401 unauthorized", "403 forbidden", "invalid credentials", "authentication failed"),
        "PACKAGE_INDEX_AUTH_FAILED",
        False,
    ),
    (
        ResolverErrorKind.NETWORK_TRANSIENT,
        (
            "connection reset",
            "connection refused",
            "temporary failure in name resolution",
            "name or service not known",
            "service unavailable",
            "too many requests",
            "http 429",
            "http 502",
            "http 503",
            "http 504",
        ),
        "DEPENDENCY_NETWORK_TRANSIENT",
        True,
    ),
    (
        ResolverErrorKind.TIMEOUT,
        ("timed out", "timeout expired", "deadline exceeded"),
        "DEPENDENCY_RESOLUTION_TIMEOUT",
        True,
    ),
    (
        ResolverErrorKind.PACKAGE_NOT_FOUND,
        ("no matching distribution found", "package was not found", "could not find a version that satisfies"),
        "DEPENDENCY_NOT_FOUND",
        False,
    ),
    (
        ResolverErrorKind.DEPENDENCY_CONFLICT,
        (
            "no solution found when resolving dependencies",
            "requirements are unsatisfiable",
            "resolutionimpossible",
            "dependency conflict",
            "incompatible constraints",
        ),
        "DEPENDENCY_CONFLICT",
        False,
    ),
)


def classify_resolver_failure(output: str) -> ResolverDiagnostic:
    """Classify bounded resolver output without changing the raw diagnostic."""

    normalized = output.casefold()
    for kind, patterns, error_code, retryable in _PATTERNS:
        if any(pattern in normalized for pattern in patterns):
            return ResolverDiagnostic(kind=kind, error_code=error_code, retryable=retryable)
    return ResolverDiagnostic(
        kind=ResolverErrorKind.INTERNAL,
        error_code="DEPENDENCY_RESOLVER_INTERNAL",
        retryable=False,
    )
