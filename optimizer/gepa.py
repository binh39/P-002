from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import dspy

from harness.models import HarnessResult
from harness.runner import run_harness_on

from .metrics import composite_score


def result_feedback(result: HarnessResult) -> str:
    """Produce evidence-grounded textual feedback for GEPA reflection."""
    if not result.build_ok:
        return f"Build: FAIL - {result.build_error}. Score is zero until tests run."
    failed = result.num_tests - result.num_passed
    return (
        f"Build: OK. {result.num_passed}/{result.num_tests} tests pass "
        f"({failed} fail). Statement coverage {result.statement_coverage:.0%}, "
        f"branch coverage {result.branch_coverage:.0%}."
    )


def gepa_metric(
    gold: Any,
    pred: Any,
    trace: Any = None,
    pred_name: str | None = None,
    pred_trace: Any = None,
):
    """Execution metric with the feedback contract required by DSPy GEPA."""
    del trace, pred_name, pred_trace
    test_code = getattr(pred, "test_code", "")
    if not isinstance(test_code, str) or not test_code.strip():
        return dspy.Prediction(score=0.0, feedback="No executable pytest module returned.")
    result = run_harness_on(gold.module_path, test_code, run_mutation=False)
    return dspy.Prediction(
        score=composite_score(result),
        feedback=result_feedback(result),
    )


def compile_gepa(
    student: dspy.Module,
    trainset: Sequence[Any],
    valset: Sequence[Any],
    *,
    reflection_lm: dspy.LM,
    auto: str = "light",
    log_dir: str | None = None,
) -> dspy.Module:
    """Compile a v2 module without ever exposing the held-out split."""
    if len(trainset) != 20 or len(valset) != 10:
        raise ValueError("v2 GEPA requires exactly 20 train and 10 validation examples")
    optimizer = dspy.GEPA(
        metric=gepa_metric,
        auto=auto,
        reflection_lm=reflection_lm,
        reflection_minibatch_size=3,
        candidate_selection_strategy="pareto",
        track_stats=True,
        track_best_outputs=True,
        log_dir=log_dir,
    )
    return optimizer.compile(
        student,
        trainset=list(trainset),
        valset=list(valset),
    )
