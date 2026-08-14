from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .metrics import (
    BRANCH_SCORE_WEIGHT,
    STATEMENT_SCORE_WEIGHT,
    aggregate_coverage_score,
)

TargetIdentity = tuple[str, str, str]


def _identity(result: dict[str, Any]) -> TargetIdentity:
    target = result["target"]
    return target["project"], target["source_file"], target["symbol"]


def _aggregate(results: Iterable[dict[str, Any]]) -> dict[str, float | int]:
    return aggregate_coverage_score(list(results))


def _load_records(artifacts_dir: Path) -> list[dict[str, Any]]:
    records = []
    for path in sorted(artifacts_dir.glob("runs/**/record.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        record["_record_path"] = str(path.resolve())
        records.append(record)
    if len(records) < 2:
        raise ValueError(
            f"Expected at least two replicate record.json files under {artifacts_dir}"
        )
    return records


def _coverage_unit_oracle(
    results_by_identity: dict[TargetIdentity, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], dict[str, float | int]]:
    rows = []
    for identity, results in sorted(results_by_identity.items()):
        scores = [result.get("score") or {} for result in results]
        statement_denominators = {
            int(score.get("num_statements", 0)) for score in scores
        }
        branch_denominators = {int(score.get("num_branches", 0)) for score in scores}
        if len(statement_denominators) != 1 or len(branch_denominators) != 1:
            raise ValueError(
                "Replicate denominators differ for "
                f"{identity[1]}::{identity[2]}"
            )
        gained_lines = {
            int(line)
            for score in scores
            for line in score.get("gained_lines", [])
        }
        gained_branches = {
            tuple(int(value) for value in branch)
            for score in scores
            for branch in score.get("gained_branches", [])
        }
        num_statements = statement_denominators.pop()
        num_branches = branch_denominators.pop()
        statement_coverage = (
            len(gained_lines) / num_statements if num_statements else 1.0
        )
        branch_coverage = (
            len(gained_branches) / num_branches if num_branches else 1.0
        )
        score = (
            STATEMENT_SCORE_WEIGHT * statement_coverage
            + BRANCH_SCORE_WEIGHT * branch_coverage
            if num_branches
            else statement_coverage
        )
        rows.append({
            "target": {
                "project": identity[0],
                "source_file": identity[1],
                "symbol": identity[2],
            },
            "score": score,
            "covered_statements": len(gained_lines),
            "num_statements": num_statements,
            "covered_branches": len(gained_branches),
            "num_branches": num_branches,
            "gained_lines": sorted(gained_lines),
            "gained_branches": [list(branch) for branch in sorted(gained_branches)],
        })
    aggregate = _aggregate([
        {"target": row["target"], "score": row} for row in rows
    ])
    return rows, aggregate


def build_calibration_report(artifacts_dir: Path) -> dict[str, Any]:
    """Summarize repeated generation runs using fixed coverage denominators."""
    records = _load_records(artifacts_dir)
    replicate_results: list[dict[str, Any]] = []
    results_by_identity: dict[TargetIdentity, list[dict[str, Any]]] = {}
    expected_identities: set[TargetIdentity] | None = None

    for index, record in enumerate(records):
        results = record.get("results") or []
        identities = {_identity(result) for result in results}
        if expected_identities is None:
            expected_identities = identities
        elif identities != expected_identities:
            missing = sorted(expected_identities - identities)
            extra = sorted(identities - expected_identities)
            raise ValueError(
                f"Replicate target sets differ; missing={missing}, extra={extra}"
            )
        outcomes = Counter(
            str(trace.get("outcome", "unknown"))
            for result in results
            for trace in result.get("attempt_traces", [])
        )
        replicate_results.append({
            "replicate": index,
            "run_id": record.get("run_id"),
            "record_path": record["_record_path"],
            "tests_workspace": record.get("tests_workspace"),
            "elapsed_seconds": record.get("elapsed_seconds"),
            "aggregate": _aggregate(results),
            "failure_taxonomy": dict(sorted(outcomes.items())),
        })
        for result in results:
            results_by_identity.setdefault(_identity(result), []).append(result)

    paired_targets = []
    for identity, results in sorted(results_by_identity.items()):
        scores = [float((result.get("score") or {}).get("score", 0.0)) for result in results]
        paired_targets.append({
            "project": identity[0],
            "source_file": identity[1],
            "symbol": identity[2],
            "scores": scores,
            "delta_last_minus_first": scores[-1] - scores[0],
            "mean": sum(scores) / len(scores),
            "minimum": min(scores),
            "maximum": max(scores),
        })

    projects = sorted({identity[0] for identity in results_by_identity})
    repo_aggregates = []
    for project in projects:
        aggregates = [
            _aggregate(
                result
                for result in record.get("results", [])
                if result.get("target", {}).get("project") == project
            )
            for record in records
        ]
        repo_aggregates.append({
            "project": project,
            "replicates": aggregates,
            "score_delta_last_minus_first": (
                float(aggregates[-1]["score"]) - float(aggregates[0]["score"])
            ),
        })

    oracle_targets, oracle_aggregate = _coverage_unit_oracle(results_by_identity)
    aggregate_scores = [
        float(replicate["aggregate"]["score"]) for replicate in replicate_results
    ]
    taxonomy = Counter()
    for replicate in replicate_results:
        taxonomy.update(replicate["failure_taxonomy"])
    return {
        "schema_version": 1,
        "artifacts_dir": str(artifacts_dir.resolve()),
        "replicate_count": len(records),
        "target_count": len(results_by_identity),
        "replicates": replicate_results,
        "aggregate_score_mean": sum(aggregate_scores) / len(aggregate_scores),
        "aggregate_score_range": max(aggregate_scores) - min(aggregate_scores),
        "paired_targets": paired_targets,
        "repo_aggregates": repo_aggregates,
        "failure_taxonomy": dict(sorted(taxonomy.items())),
        "coverage_unit_oracle": {
            "label": (
                "Preliminary union of covered lines/branches; not combined-suite proof"
            ),
            "aggregate": oracle_aggregate,
            "targets": oracle_targets,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    def percent(value: Any) -> str:
        return f"{100 * float(value):.2f}%"

    lines = [
        "# Phase 0 calibration report",
        "",
        f"- Replicates: {report['replicate_count']}",
        f"- Targets: {report['target_count']}",
        f"- Mean aggregate score: {percent(report['aggregate_score_mean'])}",
        f"- Aggregate score range: {percent(report['aggregate_score_range'])}",
        "",
        "## Replicates",
        "",
        "| Replicate | Score | Statement | Branch | Elapsed |",
        "| ---: | ---: | ---: | ---: | ---: |",
    ]
    for replicate in report["replicates"]:
        aggregate = replicate["aggregate"]
        lines.append(
            f"| {replicate['replicate']} | {percent(aggregate['score'])} | "
            f"{percent(aggregate['statement_coverage'])} | "
            f"{percent(aggregate['branch_coverage'])} | "
            f"{float(replicate.get('elapsed_seconds') or 0):.1f}s |"
        )
    lines.extend([
        "",
        "## Paired target deltas",
        "",
        "| Project | Target | Scores | Last - first |",
        "| --- | --- | --- | ---: |",
    ])
    for target in report["paired_targets"]:
        scores = ", ".join(percent(value) for value in target["scores"])
        lines.append(
            f"| {target['project']} | `{target['source_file']}::{target['symbol']}` "
            f"| {scores} | {percent(target['delta_last_minus_first'])} |"
        )
    lines.extend([
        "",
        "## Failure taxonomy",
        "",
    ])
    if report["failure_taxonomy"]:
        lines.extend(
            f"- `{outcome}`: {count}"
            for outcome, count in report["failure_taxonomy"].items()
        )
    else:
        lines.append("- No attempt trace events were recorded.")
    oracle = report["coverage_unit_oracle"]
    aggregate = oracle["aggregate"]
    lines.extend([
        "",
        "## Coverage-unit oracle",
        "",
        f"**{oracle['label']}.**",
        "",
        f"- Score: {percent(aggregate['score'])}",
        f"- Statement coverage: {percent(aggregate['statement_coverage'])}",
        f"- Branch coverage: {percent(aggregate['branch_coverage'])}",
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze repeated Phase 0 artifacts")
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args(argv)
    report = build_calibration_report(args.artifacts)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(render_markdown(report), encoding="utf-8")
    if not args.json_output and not args.markdown_output:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
