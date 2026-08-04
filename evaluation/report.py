from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from .models import BaselineEvaluation
from .statistics import paired_bootstrap

REQUIRED_BASELINES = (
    "zero_shot",
    "static_symprompt",
    "coverup",
    "bootstrap_few_shot",
    "gepa",
)
LLM_MODES = (
    "zero_shot",
    "static_symprompt",
    "bootstrap_few_shot",
    "gepa",
)


def _qualitative_examples(
    baseline: BaselineEvaluation,
    gepa: BaselineEvaluation,
    *,
    limit: int = 5,
) -> list[str]:
    baseline_rows = {row["example_id"]: row for row in baseline.per_example}
    gepa_rows = {row["example_id"]: row for row in gepa.per_example}
    shared = baseline_rows.keys() & gepa_rows.keys()

    def deltas(example_id: str) -> tuple[float, float, float]:
        before = baseline_rows[example_id]["result"]
        after = gepa_rows[example_id]["result"]
        return (
            float(after["mutation_score"]) - float(before["mutation_score"]),
            float(after["branch_coverage"]) - float(before["branch_coverage"]),
            float(after["pass_rate"]) - float(before["pass_rate"]),
        )

    selected = sorted(
        shared,
        key=lambda example_id: (
            abs(deltas(example_id)[0]),
            abs(deltas(example_id)[1]),
            abs(deltas(example_id)[2]),
            example_id,
        ),
        reverse=True,
    )[:limit]
    rows = []
    for example_id in selected:
        mutation_delta, branch_delta, pass_delta = deltas(example_id)
        direction_vector = (mutation_delta, branch_delta, pass_delta)
        direction = (
            "improved"
            if direction_vector > (0.0, 0.0, 0.0)
            else "regressed"
            if direction_vector < (0.0, 0.0, 0.0)
            else "tied"
        )
        result = gepa_rows[example_id]["result"]
        evidence = ""
        if not result.get("build_ok", False):
            error = str(result.get("build_error", "")).splitlines()
            detail = error[-1][:240] if error else "unknown"
            evidence = f" Build failure: {detail}."
        elif result.get("surviving_mutant_lines"):
            evidence = (
                " Surviving mutant lines: "
                f"{result['surviving_mutant_lines'][:12]}."
            )
        rows.append(
            f"- `{example_id}` {direction}: mutation {mutation_delta:+.1%}, "
            f"branch {branch_delta:+.1%}, pass rate {pass_delta:+.1%}."
            f"{evidence}"
        )
    return rows


def generate_report(
    evaluations: Sequence[BaselineEvaluation],
    output: str | Path,
) -> str:
    by_name = {evaluation.name: evaluation for evaluation in evaluations}
    missing = set(REQUIRED_BASELINES) - by_name.keys()
    if missing:
        raise ValueError(f"Final report is missing baselines: {sorted(missing)}")
    if len({item.holdout_digest for item in by_name.values()}) != 1:
        raise ValueError("Every baseline must use the same locked held-out set")

    rows = [
        "# Test-generation prompt optimization - held-out evaluation",
        "",
        "All methods were measured once on the same locked held-out functions "
        "through the common Docker harness.",
        "",
        "## Methodology",
        "",
        "- Coverage and mutation are scoped to the focal function. Mutation "
        "testing uses a generated mutmut patch so unrelated symbols do not "
        "affect the score.",
        "- A mutation timeout or mutation-infrastructure failure is assigned a "
        "conservative mutation score of 0 while valid build, test, and coverage "
        "measurements are retained.",
        "- Cost and latency include optimizer compilation plus held-out test "
        "generation. CoverUp cost/latency include its external generation run "
        "and replay through the same harness.",
        "",
        "## Aggregate results",
        "",
        "| Baseline | Build rate | Pass rate | Statement coverage | "
        "Branch coverage | Mutation score | Cost/run | Latency |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name in REQUIRED_BASELINES:
        item = by_name[name]
        rows.append(
            f"| {name} | {item.build_rate:.1%} | {item.pass_rate:.1%} | "
            f"{item.statement_coverage:.1%} | {item.branch_coverage:.1%} | "
            f"{item.mutation_score:.1%} | ${item.cost_usd:.4f} | "
            f"{item.latency_seconds:.2f}s |"
        )

    gepa = by_name["gepa"]
    llm_ranking = sorted(
        (by_name[name] for name in LLM_MODES),
        key=lambda item: (
            item.mutation_score,
            item.branch_coverage,
            item.pass_rate,
        ),
        reverse=True,
    )
    rows.extend(
        [
            "",
            "## Four LLM modes",
            "",
            "The primary comparison contains zero-shot, static SymPrompt, "
            "BootstrapFewShot, and GEPA. CoverUp is retained separately as the "
            "required external-tool reference.",
            "",
            "| Rank | LLM mode | Mutation score | Branch coverage | Pass rate |",
            "|---:|---|---:|---:|---:|",
        ]
    )
    for rank, item in enumerate(llm_ranking, start=1):
        rows.append(
            f"| {rank} | {item.name} | {item.mutation_score:.1%} | "
            f"{item.branch_coverage:.1%} | {item.pass_rate:.1%} |"
        )

    rows.extend(["", "## Paired analysis", ""])
    for name in (*LLM_MODES[:-1], "coverup"):
        comparison = paired_bootstrap(
            by_name[name],
            gepa,
            metric="mutation_score",
        )
        rows.append(
            f"- GEPA vs `{name}` mutation delta: "
            f"{comparison.mean_delta:+.1%} "
            f"(95% paired-bootstrap CI {comparison.confidence_low:+.1%} to "
            f"{comparison.confidence_high:+.1%}); "
            f"{comparison.improvements} improved, "
            f"{comparison.regressions} regressed, {comparison.ties} tied."
        )

    strongest = max(
        (by_name[name] for name in LLM_MODES[:-1]),
        key=lambda item: (item.mutation_score, item.branch_coverage),
    )
    rows.extend(
        [
            "",
            "## Qualitative examples",
            "",
            "GEPA is compared below with the strongest non-GEPA LLM mode "
            f"(`{strongest.name}`). The 3-5 examples with the largest measured "
            "per-function changes are shown; no LLM-as-judge is used.",
            "",
            *_qualitative_examples(strongest, gepa),
            "",
            "## Scope and next steps",
            "",
            "Memory/warm-start, full multi-role authorization, and real-time "
            "cost alerts are intentionally post-v-final extensions.",
        ]
    )
    report = "\n".join(rows) + "\n"
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(report, encoding="utf-8")
    return report
