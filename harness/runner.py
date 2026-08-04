from __future__ import annotations

import subprocess
import time
from pathlib import Path

from .models import HarnessResult
from .mutation import run_mutation_testing, symbol_line_span
from .sandbox import run_in_sandbox


def _fraction(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return min(1.0, max(0.0, number / 100.0))


def _focal_coverage(
    coverage: dict,
    source_file: Path,
    symbol: str,
) -> tuple[float, float] | None:
    files = coverage.get("files", {})
    normalized = source_file.as_posix().lower()
    candidates = [
        details
        for filename, details in files.items()
        if normalized.endswith(Path(filename).as_posix().lower())
    ]
    if len(candidates) != 1:
        return None
    details = candidates[0]
    start_line, end_line = symbol_line_span(source_file, symbol)

    def in_symbol(line: int) -> bool:
        return start_line <= int(line) <= end_line

    executed_lines = {
        int(line) for line in details.get("executed_lines", []) if in_symbol(line)
    }
    missing_lines = {
        int(line) for line in details.get("missing_lines", []) if in_symbol(line)
    }
    statement_total = len(executed_lines | missing_lines)
    statement_coverage = (
        len(executed_lines) / statement_total if statement_total else 0.0
    )

    executed_branches = {
        tuple(branch)
        for branch in details.get("executed_branches", [])
        if branch and in_symbol(branch[0])
    }
    missing_branches = {
        tuple(branch)
        for branch in details.get("missing_branches", [])
        if branch and in_symbol(branch[0])
    }
    branch_total = len(executed_branches | missing_branches)
    branch_coverage = (
        len(executed_branches) / branch_total
        if branch_total
        else statement_coverage
    )
    return statement_coverage, branch_coverage


def run_harness_on(
    module_path: str | Path,
    test_code: str,
    run_mutation: bool = True,
    *,
    timeout: int = 60,
    mutation_target: str | Path | None = None,
    mutation_symbol: str | None = None,
) -> HarnessResult:
    """Execute generated tests and return the system-wide harness contract."""
    raw = run_in_sandbox(module_path, test_code, timeout=timeout)
    duration = float(raw.get("duration_seconds", 0.0))
    if not raw.get("build_ok"):
        return HarnessResult(
            build_ok=False,
            build_error=str(raw.get("build_error", "unknown sandbox failure")),
            num_tests=0,
            num_passed=0,
            pass_rate=0.0,
            statement_coverage=0.0,
            branch_coverage=0.0,
            mutation_score=0.0,
            duration_seconds=duration,
        )

    report = raw.get("report", {})
    summary = report.get("summary", {})
    num_tests = int(summary.get("total", 0))
    num_passed = int(summary.get("passed", 0))
    pass_rate = num_passed / num_tests if num_tests else 0.0

    coverage = raw.get("coverage", {})
    totals = coverage.get("totals", {})
    statement_coverage = _fraction(totals.get("percent_covered", 0.0))
    branch_value = totals.get("percent_covered_branches")
    branch_coverage = (
        statement_coverage if branch_value is None else _fraction(branch_value)
    )
    if mutation_target is not None and mutation_symbol:
        focal = _focal_coverage(
            coverage,
            Path(mutation_target).resolve(),
            mutation_symbol,
        )
        if focal is not None:
            statement_coverage, branch_coverage = focal

    mutation_score = 0.0
    surviving_lines: list[int] = []
    if run_mutation and num_tests and pass_rate == 1.0:
        mutation_started = time.monotonic()
        try:
            mutation_score, surviving_lines = run_mutation_testing(
                module_path,
                test_code,
                mutation_target=mutation_target,
                mutation_symbol=mutation_symbol,
            )
        except (OSError, RuntimeError, subprocess.TimeoutExpired):
            # A mutation infrastructure failure must not erase valid pytest and
            # coverage evidence. Score it conservatively as zero.
            mutation_score = 0.0
            surviving_lines = []
        finally:
            duration += time.monotonic() - mutation_started

    return HarnessResult(
        build_ok=True,
        build_error="",
        num_tests=num_tests,
        num_passed=num_passed,
        pass_rate=pass_rate,
        statement_coverage=statement_coverage,
        branch_coverage=branch_coverage,
        mutation_score=mutation_score,
        surviving_mutant_lines=surviving_lines,
        duration_seconds=duration,
    )
