from __future__ import annotations

from harness.models import HarnessResult


def generate_explanation(
    baseline: HarnessResult,
    candidate: HarnessResult,
) -> str:
    """Explain measured improvements and regressions without LLM speculation."""
    parts = [
        "Branch coverage: "
        f"{baseline.branch_coverage:.0%} → {candidate.branch_coverage:.0%} "
        f"({candidate.branch_coverage - baseline.branch_coverage:+.0%}).",
        "Statement coverage: "
        f"{baseline.statement_coverage:.0%} → {candidate.statement_coverage:.0%} "
        f"({candidate.statement_coverage - baseline.statement_coverage:+.0%}).",
        "Mutation score: "
        f"{baseline.mutation_score:.0%} → {candidate.mutation_score:.0%} "
        f"({candidate.mutation_score - baseline.mutation_score:+.0%}).",
        "Pass rate: "
        f"{baseline.pass_rate:.0%} → {candidate.pass_rate:.0%} "
        f"({candidate.pass_rate - baseline.pass_rate:+.0%}).",
    ]
    fixed = set(baseline.surviving_mutant_lines) - set(
        candidate.surviving_mutant_lines
    )
    introduced = set(candidate.surviving_mutant_lines) - set(
        baseline.surviving_mutant_lines
    )
    if fixed:
        parts.append(f"Newly killed mutant lines: {sorted(fixed)}.")
    if introduced:
        parts.append(f"Regression—new surviving mutant lines: {sorted(introduced)}.")
    return " ".join(parts)
