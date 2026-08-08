from dataclasses import dataclass
from typing import Any

from .prompts import PromptBundle


@dataclass(frozen=True, slots=True)
class OptimizationTarget:
    """Immutable target passed from the web experiment snapshot to the Cloud pipeline."""

    id: str
    symbol: str
    source: str
    split: str
    source_file: str = ""
    project: str = "uploaded"


@dataclass(frozen=True, slots=True)
class OptimizationResult:
    """Normalized result returned by Duy's Cloud Run GEPA implementation."""

    candidate: PromptBundle
    score: float
    baseline_score: float
    candidate_count: int
    metric_calls: int
    gepa_result: dict[str, Any]
