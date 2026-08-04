from __future__ import annotations

from typing import Any

from harness.models import HarnessResult
from harness.runner import run_harness_on

WEIGHTS = {
    "pass_rate": 0.35,
    "mutation_score": 0.35,
    "branch_coverage": 0.20,
    "statement_coverage": 0.10,
}


def composite_score(result: HarnessResult) -> float:
    return sum(float(getattr(result, name)) * weight for name, weight in WEIGHTS.items())


def simple_metric(example: Any, pred: Any, trace: Any = None) -> float:
    """Scalar execution metric used by the v1 BootstrapFewShot compiler."""
    del trace
    test_code = getattr(pred, "test_code", "")
    if not isinstance(test_code, str) or not test_code.strip():
        return 0.0
    harness_kwargs: dict[str, Any] = {}
    if mutation_target := getattr(example, "source_path", None):
        harness_kwargs["mutation_target"] = mutation_target
    if mutation_symbol := getattr(example, "symbol", None):
        harness_kwargs["mutation_symbol"] = mutation_symbol
    result = run_harness_on(example.module_path, test_code, **harness_kwargs)
    return composite_score(result)
