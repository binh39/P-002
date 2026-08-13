from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .subprocesses import run_streamed

# pytest.ExitCode.NO_TESTS_COLLECTED.  Keep this local instead of importing
# pytest in the production coverage wrapper.
_NO_TESTS_COLLECTED = 5
_TESTS_FAILED = 1


def normalize_path(value: str | Path) -> str:
    return str(value).replace("\\", "/").lower().lstrip("./")


@dataclass(frozen=True)
class SymbolCoverage:
    source_file: str
    symbol: str
    covered_statements: int
    num_statements: int
    covered_branches: int
    num_branches: int
    executed_lines: tuple[int, ...]
    missing_lines: tuple[int, ...]
    executed_branches: tuple[tuple[int, int], ...]
    missing_branches: tuple[tuple[int, int], ...]

    @property
    def statement_coverage(self) -> float:
        return self.covered_statements / self.num_statements if self.num_statements else 1.0

    @property
    def branch_coverage(self) -> float:
        return self.covered_branches / self.num_branches if self.num_branches else 1.0


def load_report(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def _find_file(report: dict[str, Any], source_file: str) -> tuple[str, dict[str, Any]]:
    wanted = normalize_path(source_file)
    matches = [
        (name, value)
        for name, value in report.get("files", {}).items()
        if normalize_path(name) == wanted or normalize_path(name).endswith("/" + wanted)
    ]
    if not matches:
        raise KeyError(f"Source file {source_file!r} is absent from the coverage report")
    if len(matches) > 1:
        raise KeyError(f"Source file {source_file!r} is ambiguous in the coverage report")
    return matches[0]


def symbol_coverage(report: dict[str, Any], source_file: str, symbol: str) -> SymbolCoverage:
    report_name, file_data = _find_file(report, source_file)
    functions = file_data.get("functions", {})
    if symbol not in functions:
        available = ", ".join(sorted(name for name in functions if name)[:20])
        raise KeyError(f"Symbol {symbol!r} is absent from {report_name}; available: {available}")
    data = functions[symbol]
    summary = data["summary"]
    return SymbolCoverage(
        source_file=report_name,
        symbol=symbol,
        covered_statements=int(summary["covered_lines"]),
        num_statements=int(summary["num_statements"]),
        covered_branches=int(summary.get("covered_branches", 0)),
        num_branches=int(summary.get("num_branches", 0)),
        executed_lines=tuple(data.get("executed_lines", [])),
        missing_lines=tuple(data.get("missing_lines", [])),
        executed_branches=tuple(tuple(item) for item in data.get("executed_branches", [])),
        missing_branches=tuple(tuple(item) for item in data.get("missing_branches", [])),
    )


def run_coverage(
    *, project_root: Path, package_dir: Path, tests_dir: Path, output: Path,
    pytest_args: str = "", repeat_tests: int = 0,
    env: dict[str, str] | None = None,
    test_paths: Sequence[Path] | None = None,
    pytest_basetemp: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run coverage for a whole suite or an isolated subset of pytest paths."""
    output.parent.mkdir(parents=True, exist_ok=True)
    run_env = os.environ.copy()
    run_env.update(env or {})
    run_env["COVERAGE_FILE"] = str(output.with_suffix(".data").resolve())
    # Concurrent target scorers may execute the same generated module. Avoid
    # cross-process races and leftover artifacts in a shared __pycache__.
    run_env["PYTHONDONTWRITEBYTECODE"] = "1"
    selected_tests = (
        [str(path.resolve()) for path in test_paths]
        if test_paths is not None
        else [str(tests_dir.resolve())]
    )
    if not selected_tests:
        raise ValueError("test_paths must contain at least one path when provided")
    resolved_basetemp = None
    if pytest_basetemp is not None:
        resolved_basetemp = pytest_basetemp.resolve()
        resolved_basetemp.parent.mkdir(parents=True, exist_ok=True)
    run_cmd = [
        sys.executable, "-m", "coverage", "run", "--branch",
        f"--source={package_dir.resolve()}", "-m", "pytest", *selected_tests,
        "--disable-warnings", "-q", "-p", "no:cacheprovider",
        *(
            ("--basetemp", str(resolved_basetemp))
            if resolved_basetemp is not None else ()
        ),
        *(("--count", str(repeat_tests)) if repeat_tests else ()),
        *shlex.split(pytest_args, posix=os.name != "nt"),
    ]
    completed = run_streamed(
        run_cmd, cwd=project_root, env=run_env, label="coverage pytest", echo=False,
    )
    # coverage.py writes usable execution data when pytest finishes with test
    # failures (exit 1), as well as when it passes or collects no tests.  Export
    # that data so callers can retain symbol denominators while scoring a
    # failing generated suite as zero.  Collection/internal/usage errors remain
    # unmeasurable and must not be converted into coverage reports.
    if completed.returncode not in (0, _TESTS_FAILED, _NO_TESTS_COLLECTED):
        return completed
    # Compact JSON (no --pretty-print): the report is only used to score the
    # batch and is deleted afterwards, so pretty-printing just wastes disk.
    report = run_streamed(
        [sys.executable, "-m", "coverage", "json", "-o", str(output.resolve())],
        cwd=project_root, env=run_env, label="coverage json", echo=False,
    )
    if report.returncode:
        return report
    if completed.returncode == _NO_TESTS_COLLECTED:
        return subprocess.CompletedProcess(
            args=completed.args,
            returncode=0,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
    return completed
