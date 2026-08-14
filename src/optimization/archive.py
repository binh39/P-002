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
) -> tuple[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    pattern = f"candidates/evaluations/*/*/{split}/*batch*.json"
    for path in sorted(artifacts_dir.glob(pattern)):
        batch = json.loads(path.read_text(encoding="utf-8"))
        digest = str(batch.get("evaluation_digest", ""))
        if digest and batch.get("split") == split:
            batch["_cache_path"] = str(path.resolve())
            grouped[digest].append(batch)
    if evaluation_digest is not None:
        if evaluation_digest not in grouped:
            raise ValueError(
                f"No {split!r} evaluation cohort {evaluation_digest!r} was found"
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


def build_candidate_test_archive(
    *,
    project_root: Path,
    artifacts_dir: Path,
    output_dir: Path,
    sample_repos_dir: Path,
    split: str = "validation",
    evaluation_digest: str | None = None,
    allow_holdout: bool = False,
    pytest_args: str = "",
    repeat_tests: int = 5,
) -> dict[str, Any]:
    if repeat_tests < 1:
        raise ValueError("Candidate archive verification requires repeat_tests >= 1")
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
        artifacts_dir, split=split, evaluation_digest=evaluation_digest
    )
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
    if not sample_repos_dir.is_absolute():
        sample_repos_dir = project_root / sample_repos_dir
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
    batch_scores = [
        {
            "prompt_digest": batch.get("prompt_digest"),
            "replicate": batch.get("replicate", 0),
            "aggregate": aggregate_coverage_score(batch.get("results", [])),
        }
        for batch in batches
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
    (output_dir / "candidate_test_archive.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return report


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
        allow_holdout=args.allow_holdout,
        pytest_args=args.pytest_args,
        repeat_tests=args.repeat_tests,
    )
    verification = report["verification"]
    print(json.dumps({
        "split": report["split"],
        "evaluation_digest": report["evaluation_digest"],
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
