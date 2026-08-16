from __future__ import annotations

import math
import statistics
from collections.abc import Sequence
from dataclasses import asdict, dataclass

from .coveragepy import SymbolCoverage

STATEMENT_SCORE_WEIGHT = 0.3
BRANCH_SCORE_WEIGHT = 0.7


@dataclass(frozen=True)
class CoverageScore:
    score: float
    statement_gain: float
    branch_gain: float
    statement_coverage: float
    branch_coverage: float
    covered_statements: int
    num_statements: int
    covered_branches: int
    num_branches: int
    gained_lines: tuple[int, ...]
    gained_branches: tuple[tuple[int, int], ...]
    remaining_lines: tuple[int, ...]
    remaining_branches: tuple[tuple[int, int], ...]

    def as_dict(self) -> dict:
        return asdict(self)


def score_symbol(before: SymbolCoverage, after: SymbolCoverage) -> CoverageScore:
    if (before.source_file, before.symbol) != (after.source_file, after.symbol):
        raise ValueError("Cannot compare coverage for different symbols")
    missing_lines = set(before.missing_lines)
    missing_branches = set(before.missing_branches)
    gained_lines = missing_lines.intersection(after.executed_lines)
    gained_branches = missing_branches.intersection(after.executed_branches)
    statement_gain = len(gained_lines) / len(missing_lines) if missing_lines else 1.0
    branch_gain = len(gained_branches) / len(missing_branches) if missing_branches else 1.0
    score = (
        STATEMENT_SCORE_WEIGHT * statement_gain
        + BRANCH_SCORE_WEIGHT * branch_gain
        if missing_branches
        else statement_gain
    )
    return CoverageScore(
        score=score,
        statement_gain=statement_gain,
        branch_gain=branch_gain,
        statement_coverage=after.statement_coverage,
        branch_coverage=after.branch_coverage,
        covered_statements=after.covered_statements,
        num_statements=after.num_statements,
        covered_branches=after.covered_branches,
        num_branches=after.num_branches,
        gained_lines=tuple(sorted(gained_lines)),
        gained_branches=tuple(sorted(gained_branches)),
        remaining_lines=tuple(sorted(missing_lines - gained_lines)),
        remaining_branches=tuple(sorted(missing_branches - gained_branches)),
    )


def _target_identity(result: dict) -> tuple[str, str, str, str] | None:
    target = result.get("target")
    if not isinstance(target, dict):
        return None
    try:
        return (
            target["project"], target["source_file"], target["symbol"],
            target.get("split", "train"),
        )
    except KeyError:
        return None


def aggregate_coverage_score(
    results: list[dict], *, reference_results: list[dict] | None = None,
) -> dict[str, float | int]:
    """Micro-average coverage across symbols, weighted by their executable units."""
    references = {
        identity: result.get("coverage")
        for result in (reference_results or [])
        if (identity := _target_identity(result)) is not None
        and result.get("coverage")
    }
    score_data = [
        result.get("coverage")
        or (result.get("score") if isinstance(result.get("score"), dict) else None)
        for result in results
    ]
    normalized = []
    for result, score in zip(results, score_data, strict=True):
        reference = references.get(_target_identity(result))
        if score is None and reference is not None:
            score = {
                "covered_statements": 0,
                "num_statements": reference["num_statements"],
                "covered_branches": 0,
                "num_branches": reference["num_branches"],
            }
        if score is not None:
            normalized.append(score)

    if normalized and any("num_statements" not in score for score in normalized):
        value = sum(float(score["score"]) for score in normalized) / len(results)
        return {"score": value, "statement_coverage": value, "branch_coverage": value}
    if not normalized:
        legacy = [
            float(result["score"]) for result in results
            if isinstance(result.get("score"), (int, float))
        ]
        if legacy:
            value = sum(legacy) / len(results)
            return {"score": value, "statement_coverage": value, "branch_coverage": value}
        return {
            "score": 0.0, "statement_coverage": 0.0, "branch_coverage": 0.0,
            "covered_statements": 0, "num_statements": 0,
            "covered_branches": 0, "num_branches": 0,
        }

    covered_statements = sum(
        0 if score.get("valid") is False else int(score["covered_statements"])
        for score in normalized
    )
    num_statements = sum(int(score["num_statements"]) for score in normalized)
    covered_branches = sum(
        0 if score.get("valid") is False else int(score["covered_branches"])
        for score in normalized
    )
    num_branches = sum(int(score["num_branches"]) for score in normalized)
    statement_coverage = covered_statements / num_statements if num_statements else 1.0
    branch_coverage = covered_branches / num_branches if num_branches else 1.0
    score = (
        STATEMENT_SCORE_WEIGHT * statement_coverage
        + BRANCH_SCORE_WEIGHT * branch_coverage
        if num_branches
        else statement_coverage
    )
    return {
        "score": score,
        "statement_coverage": statement_coverage,
        "branch_coverage": branch_coverage,
        "covered_statements": covered_statements,
        "num_statements": num_statements,
        "covered_branches": covered_branches,
        "num_branches": num_branches,
    }


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def paired_delta_ci(
    baseline_scores: Sequence[float],
    optimized_scores: Sequence[float],
    *,
    confidence: float = 0.95,
) -> dict[str, float | int]:
    """Compare two replicate distributions with a matched-pair delta and CI.

    Baseline and optimized replicates are matched positionally (each pair is one
    independent generation draw).  When both sides have the same number of
    replicates the per-pair deltas (optimized - baseline) are averaged and a
    normal-approximation confidence interval is reported; otherwise an unpaired
    mean delta with a normal-approximation CI on the difference of means is used.

    This is the measurement the earlier lever experiments insisted on: a single
    aggregate from one draw is dominated by generation variance, so compare the
    distribution, not one mean.

    Returns:
      baseline_mean, optimized_mean, delta, delta_ci_low, delta_ci_high,
      n_pairs, promotes (strict CI improvement over the baseline mean).
    """
    base = [float(value) for value in baseline_scores]
    opt = [float(value) for value in optimized_scores]
    if not base or not opt:
        raise ValueError("paired_delta_ci requires non-empty replicate sequences")

    base_mean = _mean(base)
    opt_mean = _mean(opt)
    if len(base) == len(opt):
        deltas = [opt[i] - base[i] for i in range(len(base))]
        delta = _mean(deltas)
        n = len(deltas)
        sd = statistics.pstdev(deltas) if n > 1 else 0.0
        z = 1.96 if confidence >= 0.95 else 1.645
    else:
        delta = opt_mean - base_mean
        n = min(len(base), len(opt))
        var_base = statistics.pstdev(base) ** 2 if len(base) > 1 else 0.0
        var_opt = statistics.pstdev(opt) ** 2 if len(opt) > 1 else 0.0
        sd = math.sqrt(var_base / len(base) + var_opt / len(opt))
        z = 1.96 if confidence >= 0.95 else 1.645
    half = z * sd if sd else 0.0
    return {
        "baseline_mean": base_mean,
        "optimized_mean": opt_mean,
        "delta": delta,
        "delta_ci_low": delta - half,
        "delta_ci_high": delta + half,
        "n_pairs": n,
        "promotes": delta - half > 0.0,
    }


def build_feedback(result: CoverageScore, *, coverup_exit_code: int = 0) -> str:
    lines = [
        f"Score: {result.score:.4f}",
        f"Statement gain: {len(result.gained_lines)} newly covered; "
        f"{len(result.remaining_lines)} remain.",
        f"Branch gain: {len(result.gained_branches)} newly covered; "
        f"{len(result.remaining_branches)} remain.",
        f"Remaining lines: {list(result.remaining_lines)}",
        f"Remaining branches: {list(result.remaining_branches)}",
        "Target each remaining branch with a distinct input and a meaningful assertion.",
    ]
    if coverup_exit_code:
        lines.insert(
            1,
            f"Warning: CoverUp exited with code {coverup_exit_code}, but the generated "
            "suite passed coverage.py. This target keeps its measured score; inspect "
            "the generation log for incomplete sibling targets.",
        )
    return "\n".join(lines)
