import json
from pathlib import Path

import pytest

from src.optimization.calibration import build_calibration_report, render_markdown


def _result(project, source_file, symbol, *, lines, branches, outcome):
    return {
        "target": {
            "project": project,
            "source_file": source_file,
            "symbol": symbol,
            "split": "validation",
        },
        "score": {
            "score": 0.0,
            "covered_statements": len(lines),
            "num_statements": 4,
            "covered_branches": len(branches),
            "num_branches": 2,
            "gained_lines": lines,
            "gained_branches": branches,
            "valid": True,
        },
        "attempt_traces": [{"outcome": outcome}],
    }


def _write_record(root: Path, candidate: str, result: dict) -> None:
    path = root / "runs" / candidate / "validation" / "run" / "record.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "run_id": candidate,
        "elapsed_seconds": 2.5,
        "tests_workspace": str(root / "generated_tests" / candidate),
        "results": [result],
    }), encoding="utf-8")


def test_calibration_report_computes_paired_delta_and_coverage_unit_oracle(tmp_path):
    _write_record(
        tmp_path,
        "candidate-a",
        _result(
            "isort", "isort/main.py", "sort_imports",
            lines=[1, 2], branches=[[1, 2]], outcome="coverage_gain_saved",
        ),
    )
    _write_record(
        tmp_path,
        "candidate-b",
        _result(
            "isort", "isort/main.py", "sort_imports",
            lines=[2, 3], branches=[[1, 3]], outcome="test_error",
        ),
    )

    report = build_calibration_report(tmp_path)

    assert report["replicate_count"] == 2
    assert report["target_count"] == 1
    assert report["failure_taxonomy"] == {
        "coverage_gain_saved": 1,
        "test_error": 1,
    }
    oracle = report["coverage_unit_oracle"]["aggregate"]
    assert oracle["statement_coverage"] == pytest.approx(0.75)
    assert oracle["branch_coverage"] == pytest.approx(1.0)
    assert oracle["score"] == pytest.approx(0.925)
    assert "not combined-suite proof" in render_markdown(report)


def test_calibration_report_rejects_different_replicate_target_sets(tmp_path):
    _write_record(
        tmp_path,
        "candidate-a",
        _result(
            "isort", "isort/main.py", "sort_imports",
            lines=[1], branches=[], outcome="coverage_gain_saved",
        ),
    )
    _write_record(
        tmp_path,
        "candidate-b",
        _result(
            "isort", "isort/wrap.py", "line",
            lines=[1], branches=[], outcome="coverage_gain_saved",
        ),
    )

    with pytest.raises(ValueError, match="target sets differ"):
        build_calibration_report(tmp_path)
