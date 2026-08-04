from __future__ import annotations

from harness.models import HarnessResult


def generate_explanation(
    baseline: HarnessResult,
    candidate: HarnessResult,
) -> str:
    """Explain measured coverage and pass-rate changes without speculation."""
    parts = [
        "Branch coverage: "
        f"{baseline.branch_coverage:.0%} → {candidate.branch_coverage:.0%} "
        f"({candidate.branch_coverage - baseline.branch_coverage:+.0%}).",
        "Statement coverage: "
        f"{baseline.statement_coverage:.0%} → {candidate.statement_coverage:.0%} "
        f"({candidate.statement_coverage - baseline.statement_coverage:+.0%}).",
        "Pass rate: "
        f"{baseline.pass_rate:.0%} → {candidate.pass_rate:.0%} "
        f"({candidate.pass_rate - baseline.pass_rate:+.0%}).",
    ]
    return " ".join(parts)
