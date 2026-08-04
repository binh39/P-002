from __future__ import annotations

from typing import Any

from harness.models import HarnessResult
from harness.runner import run_harness_on

WEIGHTS = {
    "pass_rate": 0.45,
    "branch_coverage": 0.35,
    "statement_coverage": 0.20,
}


def composite_score(result: HarnessResult) -> float:
    return sum(float(getattr(result, name)) * weight for name, weight in WEIGHTS.items())


def simple_metric(example: Any, pred: Any, trace: Any = None) -> float:
    """Scalar execution metric used by the v1 BootstrapFewShot compiler."""
    del trace
    test_code = getattr(pred, "test_code", "")
    if not isinstance(test_code, str) or not test_code.strip():
        return 0.0
    result = run_harness_on(example.module_path, test_code, run_mutation=False)
    return composite_score(result)
