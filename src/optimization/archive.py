from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

from .combined_suite import _resolve_workspace, verify_tests_workspace
from .metrics import (
    BRANCH_SCORE_WEIGHT,
    STATEMENT_SCORE_WEIGHT,
    aggregate_coverage_score,
)
from .models import SymbolTarget

TargetIdentity = tuple[str, str, str, str]
CoverageUnit = tuple[TargetIdentity, str, int | tuple[int, int]]


def _identity(result: dict[str, Any]) -> TargetIdentity:
    target = result["target"]
    return (
        target["project"],
        target["source_file"],
        target["symbol"],
        target.get("split", "train"),
    )


def _load_evaluation_cohort(
    artifacts_dir: Path,
    *,
    split: str,
    evaluation_digest: str | None = None,
    source_replicates: set[int] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    pattern = f"candidates/evaluations/*/*/{split}/*batch*.json"
    for path in sorted(artifacts_dir.glob(pattern)):
        batch = json.loads(path.read_text(encoding="utf-8"))
        digest = str(batch.get("evaluation_digest", ""))
        replicate = int(batch.get("replicate", 0))
        if (
            digest
            and batch.get("split") == split
            and (source_replicates is None or replicate in source_replicates)
        ):
            batch["_cache_path"] = str(path.resolve())
            grouped[digest].append(batch)
    if evaluation_digest is not None:
        if evaluation_digest not in grouped:
            replicate_suffix = (
                f" for source replicates {sorted(source_replicates)}"
                if source_replicates is not None
                else ""
            )
            raise ValueError(
                f"No {split!r} evaluation cohort {evaluation_digest!r} was found"
                f"{replicate_suffix}"
            )
        selected_digest = evaluation_digest
    else:
        if not grouped:
            raise ValueError(f"No cached candidate evaluations found for split {split!r}")

        def cohort_rank(item: tuple[str, list[dict[str, Any]]]) -> tuple[int, int, str]:
            digest, batches = item
            largest_target_set = max(
                (len(batch.get("results", [])) for batch in batches), default=0
            )
            return largest_target_set, len(batches), digest

        selected_digest = max(grouped.items(), key=cohort_rank)[0]
    batches = grouped[selected_digest]
    if source_replicates is not None:
        observed_replicates = {int(batch.get("replicate", 0)) for batch in batches}
        missing_replicates = source_replicates - observed_replicates
        if missing_replicates:
            raise ValueError(
                f"Evaluation cohort {selected_digest!r} is missing source replicates "
                f"{sorted(missing_replicates)}"
            )
    target_sets = [
        {_identity(result) for result in batch.get("results", [])}
        for batch in batches
    ]
    if not target_sets or not target_sets[0]:
        raise ValueError("Selected evaluation cohort has no target results")
    if any(targets != target_sets[0] for targets in target_sets[1:]):
        raise ValueError(
            "Cached batches with the same evaluation digest have different target sets"
        )
    return selected_digest, batches


def _resolve_saved_test(
    artifacts_dir: Path,
    batch: dict[str, Any],
    project: str,
    configured: str,
) -> Path:
    path = Path(configured)
    if path.is_file():
        return path.resolve()
    matches: list[Path] = []
    for workspace_value in batch.get("tests_workspaces", []):
        workspace = _resolve_workspace(artifacts_dir, str(workspace_value))
        project_workspace = workspace / project
        search_root = project_workspace if project_workspace.is_dir() else workspace
        matches.extend(search_root.rglob(path.name))
    unique = sorted({match.resolve() for match in matches if match.is_file()})
    if len(unique) != 1:
        raise FileNotFoundError(
            f"Cannot resolve archived test {configured!r}; matches={len(unique)}"
        )
    return unique[0]


def collect_archive_candidates(
    artifacts_dir: Path,
    batches: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[TargetIdentity, tuple[int, int]]]:
    """Collect and content-deduplicate traced tests with their covered units."""
    denominators: dict[TargetIdentity, tuple[int, int]] = {}
    by_content: dict[tuple[str, str], dict[str, Any]] = {}
    for batch in batches:
        for result in batch.get("results", []):
            identity = _identity(result)
            coverage = result.get("coverage") or {}
            if coverage:
                denominator = (
                    int(coverage.get("num_statements", 0)),
                    int(coverage.get("num_branches", 0)),
                )
                previous = denominators.setdefault(identity, denominator)
                if previous != denominator:
                    raise ValueError(
                        "Coverage denominators differ for "
                        f"{identity[1]}::{identity[2]}"
                    )
            if not coverage or coverage.get("valid") is False:
                continue
            allowed_lines = {int(value) for value in coverage.get("gained_lines", [])}
            allowed_branches = {
                tuple(int(value) for value in branch)
                for branch in coverage.get("gained_branches", [])
            }
            for trace in result.get("attempt_traces", []):
                if trace.get("outcome") != "coverage_gain_saved" or not trace.get(
                    "saved_test"
                ):
                    continue
                gained_lines = allowed_lines.intersection(
                    int(value) for value in trace.get("gained_lines", [])
                )
                gained_branches = allowed_branches.intersection(
                    tuple(int(value) for value in branch)
                    for branch in trace.get("gained_branches", [])
                )
                units: set[CoverageUnit] = {
                    (identity, "statement", line) for line in gained_lines
                }
                units.update(
                    (identity, "branch", branch) for branch in gained_branches
                )
                if not units:
                    continue
                source = _resolve_saved_test(
                    artifacts_dir,
                    batch,
                    identity[0],
                    str(trace["saved_test"]),
                )
                digest = hashlib.sha256(source.read_bytes()).hexdigest()
                key = identity[0], digest
                item = by_content.setdefault(
                    key,
                    {
                        "id": digest[:16],
                        "project": identity[0],
                        "source": source,
                        "size_bytes": source.stat().st_size,
                        "units": set(),
                        "origins": [],
                    },
                )
                item["units"].update(units)
                item["origins"].append({
                    "prompt_digest": batch.get("prompt_digest"),
                    "evaluation_digest": batch.get("evaluation_digest"),
                    "replicate": batch.get("replicate", 0),
                    "target": result["target"],
                })
    return sorted(by_content.values(), key=lambda item: item["id"]), denominators


def select_greedy_archive(
    candidates: list[dict[str, Any]],
    denominators: dict[TargetIdentity, tuple[int, int]],
) -> tuple[list[dict[str, Any]], set[CoverageUnit]]:
    """Select a compact weighted set cover aligned with the production metric."""
    statement_total = sum(value[0] for value in denominators.values())
    branch_total = sum(value[1] for value in denominators.values())
    statement_weight = (
        (STATEMENT_SCORE_WEIGHT if branch_total else 1.0) / statement_total
        if statement_total
        else 0.0
    )
    branch_weight = BRANCH_SCORE_WEIGHT / branch_total if branch_total else 0.0

    def unit_weight(unit: CoverageUnit) -> float:
        return statement_weight if unit[1] == "statement" else branch_weight

    selected: list[dict[str, Any]] = []
    covered: set[CoverageUnit] = set()
    remaining = list(candidates)
    while remaining:
        ranked = []
        for item in remaining:
            marginal = item["units"] - covered
            ranked.append((
                sum(unit_weight(unit) for unit in marginal),
                len(marginal),
                -int(item["size_bytes"]),
                item,
                marginal,
            ))
        weight, count, _, best, marginal = max(
            ranked, key=lambda row: (row[0], row[1], row[2])
        )
        if weight <= 0.0 or count == 0:
            break
        selected.append(best)
        covered.update(marginal)
        remaining.remove(best)
    return selected, covered


def _estimated_aggregate(
    covered: set[CoverageUnit],
    denominators: dict[TargetIdentity, tuple[int, int]],
) -> dict[str, float | int]:
    covered_statements = sum(unit[1] == "statement" for unit in covered)
    covered_branches = sum(unit[1] == "branch" for unit in covered)
    num_statements = sum(value[0] for value in denominators.values())
    num_branches = sum(value[1] for value in denominators.values())
    statement = covered_statements / num_statements if num_statements else 1.0
    branch = covered_branches / num_branches if num_branches else 1.0
    score = (
        STATEMENT_SCORE_WEIGHT * statement + BRANCH_SCORE_WEIGHT * branch
        if num_branches
        else statement
    )
    return {
        "score": score,
        "statement_coverage": statement,
        "branch_coverage": branch,
        "covered_statements": covered_statements,
        "num_statements": num_statements,
        "covered_branches": covered_branches,
        "num_branches": num_branches,
    }


def _target_estimated_score(
    identity: TargetIdentity,
    covered: set[CoverageUnit],
    denominators: dict[TargetIdentity, tuple[int, int]],
) -> float:
    target_units = {unit for unit in covered if unit[0] == identity}
    return float(_estimated_aggregate(target_units, {identity: denominators[identity]})["score"])


def select_sequential_archive_batches(
    artifacts_dir: Path,
    batches: list[dict[str, Any]],
    *,
    stages: list[tuple[str, int]],
    target_stop_score: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Select cached target generations using a fixed, auditable stage policy."""
    if not 0.0 < target_stop_score <= 1.0:
        raise ValueError("Sequential archive target_stop_score must be in (0, 1]")
    if not stages:
        raise ValueError("Sequential archive requires at least one prompt:replicate stage")
    if len(set(stages)) != len(stages):
        raise ValueError("Sequential archive stages must be unique")
    if any(not prompt_digest or replicate < 0 for prompt_digest, replicate in stages):
        raise ValueError("Sequential archive stages require a prompt digest and non-negative replicate")

    by_stage: dict[tuple[str, int], dict[str, Any]] = {}
    for batch in batches:
        key = str(batch.get("prompt_digest", "")), int(batch.get("replicate", 0))
        if key in by_stage:
            raise ValueError(f"Duplicate cached evaluation batch for stage {key[0]}:{key[1]}")
        by_stage[key] = batch
    missing = [f"{prompt}:{replicate}" for prompt, replicate in stages if (prompt, replicate) not in by_stage]
    if missing:
        raise ValueError("Missing cached sequential archive stages: " + ", ".join(missing))

    _, denominators = collect_archive_candidates(artifacts_dir, [by_stage[stages[0]]])
    if not denominators:
        raise ValueError("The first sequential archive stage has no coverage denominators")
    expected_identities = {
        _identity(result) for result in by_stage[stages[0]].get("results", [])
    }
    missing_denominators = expected_identities - set(denominators)
    if missing_denominators:
        raise ValueError(
            "The first sequential archive stage is missing coverage denominators for "
            f"{len(missing_denominators)} target(s)"
        )
    identities = set(denominators)
    selected_batches: list[dict[str, Any]] = []
    covered: set[CoverageUnit] = set()
    stage_rows: list[dict[str, Any]] = []
    target_generation_calls = 0
    for index, stage in enumerate(stages):
        eligible = (
            identities
            if index == 0
            else {
                identity
                for identity in identities
                if _target_estimated_score(identity, covered, denominators) < target_stop_score
            }
        )
        if not eligible:
            break
        source_batch = by_stage[stage]
        filtered_batch = {
            **source_batch,
            "results": [
                result
                for result in source_batch.get("results", [])
                if _identity(result) in eligible
            ],
        }
        stage_candidates, _ = collect_archive_candidates(artifacts_dir, [filtered_batch])
        before = set(covered)
        for candidate in stage_candidates:
            covered.update(candidate["units"])
        marginal = covered - before
        target_generation_calls += len(eligible)
        selected_batches.append(filtered_batch)
        aggregate = _estimated_aggregate(covered, denominators)
        stage_rows.append({
            "stage": index,
            "prompt_digest": stage[0],
            "replicate": stage[1],
            "eligible_target_count": len(eligible),
            "candidate_test_count": len(stage_candidates),
            "marginal_coverage_units": len(marginal),
            "estimated_aggregate_score": aggregate["score"],
            "targets_at_stop_score": sum(
                _target_estimated_score(identity, covered, denominators) >= target_stop_score
                for identity in identities
            ),
        })

    exhaustive_calls = len(stages) * len(identities)
    cohort_exhaustive_calls = len(batches) * len(identities)
    return selected_batches, {
        "kind": "cost_aware_sequential",
        "target_stop_score": target_stop_score,
        "stages_requested": [
            {"prompt_digest": prompt, "replicate": replicate}
            for prompt, replicate in stages
        ],
        "stages_executed": stage_rows,
        "target_count": len(identities),
        "target_generation_calls": target_generation_calls,
        "exhaustive_target_generation_calls": exhaustive_calls,
        "cohort_exhaustive_target_generation_calls": cohort_exhaustive_calls,
        "target_generation_savings": (
            1.0 - target_generation_calls / exhaustive_calls if exhaustive_calls else 0.0
        ),
        "cohort_target_generation_savings": (
            1.0 - target_generation_calls / cohort_exhaustive_calls
            if cohort_exhaustive_calls
            else 0.0
        ),
        "cost_proxy_meaning": (
            "One target generation at one prompt/replicate stage; provider retries and tokens are not included"
        ),
        "estimated_aggregate": _estimated_aggregate(covered, denominators),
    }


def _materialize_candidate_test_archive(
    *,
    project_root: Path,
    artifacts_dir: Path,
    output_dir: Path,
    sample_repos_dir: Path,
    split: str,
    selected_digest: str,
    batches: list[dict[str, Any]],
    comparison_batches: list[dict[str, Any]] | None,
    pytest_args: str,
    repeat_tests: int,
    report_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    candidates, denominators = collect_archive_candidates(artifacts_dir, batches)
    if not candidates:
        raise ValueError("No valid coverage-gaining generated tests were found")
    selected, covered = select_greedy_archive(candidates, denominators)
    tests_root = output_dir / "tests"
    tests_root.mkdir(parents=True)
    copied_counts: dict[str, int] = defaultdict(int)
    selected_rows = []
    for index, item in enumerate(selected):
        project_dir = tests_root / item["project"]
        project_dir.mkdir(parents=True, exist_ok=True)
        destination = project_dir / f"test_archive_{index:04d}_{item['id']}.py"
        shutil.copyfile(item["source"], destination)
        copied_counts[item["project"]] += 1
        selected_rows.append({
            "id": item["id"],
            "project": item["project"],
            "destination": str(destination),
            "size_bytes": item["size_bytes"],
            "covered_unit_count": len(item["units"]),
            "origins": item["origins"],
        })

    first_results = batches[0]["results"]
    targets = [SymbolTarget.from_dict(result["target"]) for result in first_results]
    verification = verify_tests_workspace(
        project_root=project_root,
        tests_root=tests_root,
        targets=targets,
        output_dir=output_dir,
        sample_repos_dir=sample_repos_dir,
        copied_counts=dict(copied_counts),
        pytest_args=pytest_args,
        repeat_tests=repeat_tests,
    )
    comparison_batches = comparison_batches or batches
    batch_scores = [
        {
            "prompt_digest": batch.get("prompt_digest"),
            "replicate": batch.get("replicate", 0),
            "aggregate": aggregate_coverage_score(batch.get("results", [])),
        }
        for batch in comparison_batches
    ]
    best_single = max(batch_scores, key=lambda row: float(row["aggregate"]["score"]))
    verified_aggregate = verification.get("aggregate")
    report = {
        "schema_version": 1,
        "kind": "candidate_test_archive",
        "split": split,
        "evaluation_digest": selected_digest,
        "selection_scope": (
            "Archive selection is isolated from GEPA prompt metrics and this split only"
        ),
        "candidate_test_count": len(candidates),
        "selected_test_count": len(selected),
        "selected_tests": selected_rows,
        "estimated_archive_aggregate": _estimated_aggregate(covered, denominators),
        "best_single_candidate": best_single,
        "verification": verification,
        "verified_gain_vs_best_single": (
            float(verified_aggregate["score"])
            - float(best_single["aggregate"]["score"])
            if verified_aggregate is not None
            else None
        ),
    }
    if report_metadata:
        overlap = set(report).intersection(report_metadata)
        if overlap:
            raise ValueError(f"Archive report metadata overlaps reserved keys: {sorted(overlap)}")
        report.update(report_metadata)
    (output_dir / "candidate_test_archive.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return report


def build_candidate_test_archive(
    *,
    project_root: Path,
    artifacts_dir: Path,
    output_dir: Path,
    sample_repos_dir: Path,
    split: str = "validation",
    evaluation_digest: str | None = None,
    source_replicates: set[int] | None = None,
    allow_holdout: bool = False,
    pytest_args: str = "",
    repeat_tests: int = 5,
) -> dict[str, Any]:
    if repeat_tests < 1:
        raise ValueError("Candidate archive verification requires repeat_tests >= 1")
    if source_replicates is not None and (
        not source_replicates or any(value < 0 for value in source_replicates)
    ):
        raise ValueError("Source replicates must be a non-empty set of non-negative integers")
    if split == "test" and not allow_holdout:
        raise ValueError(
            "The test split is locked. Build the archive from train/validation, "
            "or explicitly pass allow_holdout only for a final one-shot report."
        )
    project_root = project_root.resolve()
    artifacts_dir = artifacts_dir.resolve()
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"Archive output already exists: {output_dir}")
    selected_digest, batches = _load_evaluation_cohort(
        artifacts_dir,
        split=split,
        evaluation_digest=evaluation_digest,
        source_replicates=source_replicates,
    )
    if not sample_repos_dir.is_absolute():
        sample_repos_dir = project_root / sample_repos_dir
    return _materialize_candidate_test_archive(
        project_root=project_root,
        artifacts_dir=artifacts_dir,
        output_dir=output_dir,
        sample_repos_dir=sample_repos_dir,
        split=split,
        selected_digest=selected_digest,
        batches=batches,
        comparison_batches=None,
        pytest_args=pytest_args,
        repeat_tests=repeat_tests,
        report_metadata={
            "source_replicates": (
                sorted(source_replicates) if source_replicates is not None else None
            )
        },
    )


def build_sequential_candidate_test_archive(
    *,
    project_root: Path,
    artifacts_dir: Path,
    output_dir: Path,
    sample_repos_dir: Path,
    stages: list[tuple[str, int]],
    target_stop_score: float = 0.80,
    split: str = "validation",
    evaluation_digest: str | None = None,
    allow_holdout: bool = False,
    pytest_args: str = "",
    repeat_tests: int = 5,
) -> dict[str, Any]:
    if repeat_tests < 1:
        raise ValueError("Sequential archive verification requires repeat_tests >= 1")
    if not stages:
        raise ValueError("Sequential archive requires at least one prompt:replicate stage")
    if any(not prompt_digest or replicate < 0 for prompt_digest, replicate in stages):
        raise ValueError("Sequential archive stages require a prompt digest and non-negative replicate")
    if split == "test" and not allow_holdout:
        raise ValueError(
            "The test split is locked. Build the sequential archive from train/validation, "
            "or explicitly pass allow_holdout only for a final one-shot report."
        )
    project_root = project_root.resolve()
    artifacts_dir = artifacts_dir.resolve()
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"Archive output already exists: {output_dir}")
    source_replicates = {replicate for _, replicate in stages}
    selected_digest, batches = _load_evaluation_cohort(
        artifacts_dir,
        split=split,
        evaluation_digest=evaluation_digest,
        source_replicates=source_replicates,
    )
    selected_batches, policy = select_sequential_archive_batches(
        artifacts_dir,
        batches,
        stages=stages,
        target_stop_score=target_stop_score,
    )
    if not sample_repos_dir.is_absolute():
        sample_repos_dir = project_root / sample_repos_dir
    return _materialize_candidate_test_archive(
        project_root=project_root,
        artifacts_dir=artifacts_dir,
        output_dir=output_dir,
        sample_repos_dir=sample_repos_dir,
        split=split,
        selected_digest=selected_digest,
        batches=selected_batches,
        comparison_batches=batches,
        pytest_args=pytest_args,
        repeat_tests=repeat_tests,
        report_metadata={
            "source_replicates": sorted(source_replicates),
            "sequential_policy": policy,
        },
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build and verify a split-locked greedy candidate test archive"
    )
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument(
        "--sample-repos-dir", type=Path, default=Path("src/sample_repo")
    )
    parser.add_argument("--split", default="validation")
    parser.add_argument("--evaluation-digest")
    parser.add_argument(
        "--source-replicate",
        dest="source_replicates",
        type=int,
        action="append",
        help="Only archive tests from this generation replicate; may be repeated",
    )
    parser.add_argument("--allow-holdout", action="store_true")
    parser.add_argument("--pytest-args", default="")
    parser.add_argument("--repeat-tests", type=int, default=5)
    args = parser.parse_args(argv)
    report = build_candidate_test_archive(
        project_root=args.project_root,
        artifacts_dir=args.artifacts,
        output_dir=args.output_dir,
        sample_repos_dir=args.sample_repos_dir,
        split=args.split,
        evaluation_digest=args.evaluation_digest,
        source_replicates=(
            set(args.source_replicates) if args.source_replicates is not None else None
        ),
        allow_holdout=args.allow_holdout,
        pytest_args=args.pytest_args,
        repeat_tests=args.repeat_tests,
    )
    verification = report["verification"]
    print(json.dumps({
        "split": report["split"],
        "evaluation_digest": report["evaluation_digest"],
        "source_replicates": report["source_replicates"],
        "candidate_test_count": report["candidate_test_count"],
        "selected_test_count": report["selected_test_count"],
        "verified": verification["verified"],
        "archive_aggregate": verification["aggregate"],
        "best_single_candidate": report["best_single_candidate"],
        "verified_gain_vs_best_single": report["verified_gain_vs_best_single"],
    }, indent=2))
    return 0 if verification["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
