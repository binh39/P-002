from __future__ import annotations

from pathlib import Path

from harness.runner import run_harness_on


def check_coverage_gaps(
    module_path: str | Path,
    current_test_code: str,
) -> str:
    """Execute a draft without mutation testing and summarize remaining quality gaps."""
    result = run_harness_on(module_path, current_test_code, run_mutation=False)
    if not result.build_ok:
        return f"Test build failed: {result.build_error}"
    failed = result.num_tests - result.num_passed
    return (
        f"Current coverage: statement {result.statement_coverage:.0%}, "
        f"branch {result.branch_coverage:.0%}. {failed} test(s) fail."
    )


def run_test_draft(module_path: str | Path, test_code: str) -> str:
    """Execute a draft in the sandbox and return concise runtime evidence."""
    result = run_harness_on(module_path, test_code, run_mutation=False)
    status = "OK" if result.build_ok and result.pass_rate == 1.0 else "ERROR"
    return (
        f"[{status}] {result.num_passed}/{result.num_tests} pass, "
        f"statement {result.statement_coverage:.0%}, "
        f"branch {result.branch_coverage:.0%}"
    )
