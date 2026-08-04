from __future__ import annotations

from typing import Any, NotRequired, TypedDict

import dspy


class OptimizationState(TypedDict):
    experiment_id: str
    module_path: str
    trainset: list[Any]
    valset: list[Any]
    budget_limit_usd: float
    reflection_lm: dspy.LM
    baseline_prompt: NotRequired[str]
    baseline_module: NotRequired[dspy.Module]
    optimized_module: NotRequired[dspy.Module]
    gepa_log_dir: NotRequired[str]
