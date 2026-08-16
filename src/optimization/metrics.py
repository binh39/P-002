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
) -> dict[str, float | int | bool | None]:
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
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")

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
        if n < 2:
            standard_error = math.inf
            degrees_of_freedom = 0.0
        else:
            standard_error = statistics.stdev(deltas) / math.sqrt(n)
            degrees_of_freedom = float(n - 1)
    else:
        delta = opt_mean - base_mean
        n = min(len(base), len(opt))
        if len(base) < 2 or len(opt) < 2:
            standard_error = math.inf
            degrees_of_freedom = 0.0
        else:
            base_term = statistics.variance(base) / len(base)
            opt_term = statistics.variance(opt) / len(opt)
            standard_error = math.sqrt(base_term + opt_term)
            denominator = (
                (base_term**2) / (len(base) - 1)
                + (opt_term**2) / (len(opt) - 1)
            )
            degrees_of_freedom = (
                ((base_term + opt_term) ** 2) / denominator
                if denominator
                else math.inf
            )

    if math.isinf(standard_error):
        delta_ci_low = None
        delta_ci_high = None
        reported_standard_error = None
    else:
        critical = _student_t_critical(confidence, degrees_of_freedom)
        half = critical * standard_error
        delta_ci_low = delta - half
        delta_ci_high = delta + half
        reported_standard_error = standard_error
    return {
        "baseline_mean": base_mean,
        "optimized_mean": opt_mean,
        "delta": delta,
        "delta_ci_low": delta_ci_low,
        "delta_ci_high": delta_ci_high,
        "n_pairs": n,
        "confidence": confidence,
        "standard_error": reported_standard_error,
        "promotes": delta_ci_low is not None and delta_ci_low > 0.0,
    }


def _student_t_critical(confidence: float, degrees_of_freedom: float) -> float:
    """Return a two-sided Student-t critical value without a SciPy dependency."""
    if degrees_of_freedom <= 0:
        return math.inf
    probability = (1.0 + confidence) / 2.0
    z = statistics.NormalDist().inv_cdf(probability)
    if math.isinf(degrees_of_freedom):
        return z
    if math.isclose(confidence, 0.95) and degrees_of_freedom.is_integer():
        critical_95 = (
            12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306,
            2.262, 2.228, 2.201, 2.179, 2.160, 2.145, 2.131, 2.120,
            2.110, 2.101, 2.093, 2.086, 2.080, 2.074, 2.069, 2.064,
            2.060, 2.056, 2.052, 2.048, 2.045, 2.042,
        )
        integer_df = int(degrees_of_freedom)
        if integer_df <= len(critical_95):
            return critical_95[integer_df - 1]
    # Cornish-Fisher expansion for the Student-t quantile. It is accurate for
    # the replicate counts used here and, unlike a normal interval, widens
    # small-sample comparisons appropriately.
    df = degrees_of_freedom
    return (
        z
        + (z**3 + z) / (4.0 * df)
        + (5.0 * z**5 + 16.0 * z**3 + 3.0 * z) / (96.0 * df**2)
        + (3.0 * z**7 + 19.0 * z**5 + 17.0 * z**3 - 15.0 * z)
        / (384.0 * df**3)
    )


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
