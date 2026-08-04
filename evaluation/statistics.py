from __future__ import annotations

import random
from dataclasses import dataclass

from .models import BaselineEvaluation


@dataclass(frozen=True, slots=True)
class PairedComparison:
    metric: str
    mean_delta: float
    confidence_low: float
    confidence_high: float
    regressions: int
    improvements: int
    ties: int


def paired_bootstrap(
    baseline: BaselineEvaluation,
    candidate: BaselineEvaluation,
    *,
    metric: str,
    samples: int = 10_000,
    seed: int = 7,
) -> PairedComparison:
    if baseline.holdout_digest != candidate.holdout_digest:
        raise ValueError("Paired comparison requires the same held-out examples")
    baseline_rows = {
        row["example_id"]: float(row["result"][metric])
        for row in baseline.per_example
    }
    candidate_rows = {
        row["example_id"]: float(row["result"][metric])
        for row in candidate.per_example
    }
    if baseline_rows.keys() != candidate_rows.keys():
        raise ValueError("Paired comparison requires matching example identities")
    differences = [
        candidate_rows[key] - baseline_rows[key] for key in baseline_rows
    ]
    if not differences:
        raise ValueError("Paired comparison requires at least one result")
    rng = random.Random(seed)
    bootstrapped = sorted(
        sum(rng.choice(differences) for _ in differences) / len(differences)
        for _ in range(samples)
    )
    low_index = int(0.025 * (samples - 1))
    high_index = int(0.975 * (samples - 1))
    return PairedComparison(
        metric=metric,
        mean_delta=sum(differences) / len(differences),
        confidence_low=bootstrapped[low_index],
        confidence_high=bootstrapped[high_index],
        regressions=sum(delta < 0 for delta in differences),
        improvements=sum(delta > 0 for delta in differences),
        ties=sum(delta == 0 for delta in differences),
    )
