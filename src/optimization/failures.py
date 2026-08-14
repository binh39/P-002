from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

_EXCEPTION_LINE = re.compile(
    r"(?P<error_type>[A-Za-z_][\w.]*(?:Error|Exception|Timeout|Failure))"
    r"(?::\s*(?P<message>.*))?\s*$"
)
_PYTHON_FRAME = re.compile(
    r'File\s+["\'](?P<path>[^"\']+)["\'],\s*line\s*'
    r"(?P<line>\d+)(?:,\s*in\s*(?P<function>[^\r\n]+))?"
)
_PYTEST_FRAME = re.compile(
    r"(?m)^\s*(?P<path>(?:[A-Za-z]:)?[^\r\n:]*?\.py):"
    r"(?P<line>\d+)(?::\s*in\s*(?P<function>[^\r\n]+))?"
)
_INTERNAL_FRAME_PARTS = (
    "site-packages",
    "\\_pytest\\",
    "/_pytest/",
    "\\importlib\\",
    "/importlib/",
)
_ASSERT_COMPARISON = re.compile(
    r"\bassert\s+(?P<actual>.+?)\s+"
    r"(?P<operator>==|!=|is\s+not|is)\s+(?P<expected>.+)$"
)
_EXPECTED_GOT = re.compile(
    r"expected\s+(?P<expected>.+?)(?:,|;)\s*(?:but\s+)?got\s+(?P<actual>.+)",
    re.IGNORECASE,
)


def _exception_details(error: str) -> tuple[str | None, str]:
    fallback: tuple[str, str] | None = None
    for raw_line in reversed(error.splitlines()):
        line = raw_line.strip()
        if line.startswith("E "):
            line = line[2:].strip()
        match = _EXCEPTION_LINE.search(line)
        if match:
            details = (
                match.group("error_type").rsplit(".", 1)[-1],
                (match.group("message") or "").strip()[:500],
            )
            if details[1]:
                return details
            fallback = fallback or details
    return fallback or (None, "")


def _actionable_frame(error: str) -> dict[str, Any] | None:
    frames: list[tuple[int, dict[str, Any]]] = []
    for pattern in (_PYTHON_FRAME, _PYTEST_FRAME):
        for match in pattern.finditer(error):
            path = match.group("path").strip()
            lowered = path.lower()
            if path.startswith("<") or any(
                part in lowered for part in _INTERNAL_FRAME_PARTS
            ):
                continue
            frame: dict[str, Any] = {
                "path": path,
                "line": int(match.group("line")),
            }
            function = (match.group("function") or "").strip()
            if function:
                frame["function"] = function
            basename = re.split(r"[/\\]", lowered)[-1]
            if basename.startswith(("tmp_test_", "test_")):
                priority = 3
            elif "sample_repo" in lowered:
                priority = 2
            else:
                priority = 1
            frames.append((priority * 10**9 + match.start(), frame))
    if not frames:
        return None
    return max(frames, key=lambda item: item[0])[1]


def _assertion_values(error: str) -> dict[str, str]:
    for raw_line in error.splitlines():
        line = raw_line.strip()
        if line.startswith("E "):
            line = line[2:].strip()
        comparison = _ASSERT_COMPARISON.search(line)
        if comparison:
            return {
                "actual": comparison.group("actual").strip()[:300],
                "expected": comparison.group("expected").strip()[:300],
                "comparison": " ".join(comparison.group("operator").split()),
            }
        expected_got = _EXPECTED_GOT.search(line)
        if expected_got:
            return {
                "actual": expected_got.group("actual").strip()[:300],
                "expected": expected_got.group("expected").strip()[:300],
            }
    return {}


def _error_failure_type(error_type: str | None, error: str) -> tuple[str, str]:
    lowered = error.lower()
    if error_type == "AssertionError":
        return "assertion", "assertion_error"
    if error_type in {"ImportError", "ModuleNotFoundError"}:
        return "collection", "import_error"
    if error_type in {"SyntaxError", "IndentationError"}:
        return "collection", "syntax_error"
    if error_type and "timeout" in error_type.lower():
        return "execution", "timeout"
    if "error collecting" in lowered or "collection error" in lowered:
        return "collection", "collection_error"
    if error_type:
        snake = re.sub(r"(?<!^)(?=[A-Z])", "_", error_type).lower()
        return "execution", snake
    return "execution", "test_error"


def classify_attempt_failure(
    attempt: Mapping[str, Any],
    previous_attempt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a compact, stable taxonomy for one CoverUp trace event.

    Raw stderr remains available separately. This record points reflection at
    the failure stage and the most actionable user/repository frame without
    requiring the model to rediscover both from a long pytest transcript.
    """

    outcome = str(attempt.get("outcome", ""))
    error = str(attempt.get("execution_error", "") or "")
    error_type, message = _exception_details(error)
    frame = _actionable_frame(error)

    if outcome == "coverage_gain_saved":
        remaining = len(attempt.get("remaining_lines", [])) + len(
            attempt.get("remaining_branches", [])
        )
        if not remaining:
            return {}
        result: dict[str, Any] = {
            "failure_stage": "coverage",
            "failure_type": "partial_coverage",
        }
    elif outcome == "no_coverage_gain_unrepairable":
        result = {
            "failure_stage": "coverage",
            "failure_type": "no_coverage_gain",
        }
    elif outcome == "coverage_timeout":
        result = {"failure_stage": "execution", "failure_type": "timeout"}
    elif outcome in {
        "model_request_failed",
        "malformed_response",
        "empty_response",
        "missing_python_block",
    }:
        result = {
            "failure_stage": "generation",
            "failure_type": outcome,
        }
    elif outcome == "missing_imports":
        result = {
            "failure_stage": "collection",
            "failure_type": "missing_import",
        }
    elif outcome == "max_attempts_exhausted":
        result = {
            "failure_stage": "repair",
            "failure_type": "max_attempts_exhausted",
        }
        if previous_attempt is not None:
            root = classify_attempt_failure(previous_attempt)
            if root:
                result["root_failure_stage"] = root.get("failure_stage")
                result["root_failure_type"] = root.get("failure_type")
                error_type = error_type or root.get("error_type")
                message = message or str(root.get("error_message", ""))
                frame = frame or root.get("actionable_frame")
                for key in ("actual", "expected", "comparison"):
                    if key in root:
                        result[key] = root[key]
    elif outcome in {"test_error", "test_error_unrepairable"} or error:
        stage, failure_type = _error_failure_type(error_type, error)
        result = {"failure_stage": stage, "failure_type": failure_type}
        if outcome == "test_error_unrepairable":
            result["terminal_reason"] = outcome
    else:
        return {}

    if error_type:
        result["error_type"] = error_type
    if message:
        result["error_message"] = message
    if frame:
        result["actionable_frame"] = frame
    if result.get("failure_stage") == "assertion":
        result.update(_assertion_values(error))
    return result
