"""Tiny pytest result plugin loaded explicitly by the sandbox agent."""

from __future__ import annotations

import json
import os
from pathlib import Path

_counts = {"collected": 0, "passed": 0, "failed": 0, "skipped": 0}


def pytest_collection_finish(session) -> None:
    _counts["collected"] = len(session.items)


def pytest_runtest_logreport(report) -> None:
    if report.when == "call":
        if report.passed:
            outcome = "passed"
        elif report.failed:
            outcome = "failed"
        else:
            outcome = "skipped"
    elif report.when == "setup" and (report.failed or report.skipped):
        outcome = "failed" if report.failed else "skipped"
    else:
        return
    _counts[outcome] += 1


def pytest_sessionfinish(session, exitstatus) -> None:
    del session, exitstatus
    destination = os.environ.get("SANDBOX_TEST_COUNTS_FILE")
    if destination:
        Path(destination).write_text(json.dumps(_counts, sort_keys=True), encoding="utf-8")
