from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def compute_pareto_frontier(
    candidates: Sequence[Mapping[str, Any]],
    *,
    maximize: Sequence[str],
    minimize: Sequence[str],
) -> list[Mapping[str, Any]]:
    """Return candidates not dominated across all requested objectives."""
    if not maximize and not minimize:
        raise ValueError("At least one Pareto objective is required")
    required = set(maximize) | set(minimize)
    for candidate in candidates:
        missing = required - candidate.keys()
        if missing:
            raise KeyError(f"Candidate is missing Pareto fields: {sorted(missing)}")

    frontier = []
    for candidate in candidates:
        dominated = False
        for other in candidates:
            if other is candidate:
                continue
            better_or_equal = all(other[field] >= candidate[field] for field in maximize)
            better_or_equal = better_or_equal and all(
                other[field] <= candidate[field] for field in minimize
            )
            strictly_better = any(
                other[field] > candidate[field] for field in maximize
            ) or any(other[field] < candidate[field] for field in minimize)
            if better_or_equal and strictly_better:
                dominated = True
                break
        if not dominated:
            frontier.append(candidate)
    return frontier
