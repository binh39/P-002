from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import dspy

from .metrics import simple_metric


def compile_bootstrap(
    student: dspy.Module,
    trainset: Sequence[Any],
    *,
    max_bootstrapped_demos: int = 4,
    max_labeled_demos: int = 4,
) -> dspy.Module:
    """Compile the v1 module with a bounded BootstrapFewShot optimizer."""
    if not 5 <= len(trainset) <= 10:
        raise ValueError("v1 BootstrapFewShot requires a dataset of 5 to 10 functions")
    optimizer = dspy.BootstrapFewShot(
        metric=simple_metric,
        max_bootstrapped_demos=max_bootstrapped_demos,
        max_labeled_demos=max_labeled_demos,
    )
    return optimizer.compile(student, trainset=list(trainset))
