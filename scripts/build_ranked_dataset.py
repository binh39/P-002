"""Build a merged, branch-ranked train/validation/test benchmark dataset.

Every function of the given Python projects is measured statically (branch
count, statement count, source line count) and sorted by:

1. number of branches, descending;
2. number of statements, descending;
3. number of source lines, descending;
4. project name, then source file, then symbol (ascending, deterministic).

Selected functions are allocated proportionally by project, with ranks inside
each project interleaved across train, validation and the locked test split.

Example (defaults, from the repository root):

    python scripts/build_ranked_dataset.py

Custom limits:

    python scripts/build_ranked_dataset.py --train-limit 100 \
        --validation-limit 60 --test-limit 60
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.optimization.dataset_builder import (  # noqa: E402
    FunctionInfo,
    build_dataset,
)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description=(
            "Rank all functions of Python projects by branch count and emit a "
            "train/validation/test JSONL dataset"
        )
    )
    result.add_argument(
        "--projects-root",
        type=Path,
        default=ROOT / "src" / "sample_repo",
        help="Directory that contains one subdirectory per project",
    )
    result.add_argument(
        "--projects",
        nargs="+",
        default=["isort", "mlxtend", "typesystem", "mimesis"],
        help="Project names; each must contain a package directory with the same name",
    )
    result.add_argument("--train-limit", type=int, default=150)
    result.add_argument("--validation-limit", type=int, default=300)
    result.add_argument("--test-limit", type=int, default=300)
    result.add_argument(
        "--output",
        type=Path,
        default=ROOT / "eval" / "prompt_optimization" / "datasets" / "data_symbols.jsonl",
    )
    result.add_argument(
        "--ranked-output",
        type=Path,
        default=ROOT / "eval" / "prompt_optimization" / "datasets" / "data_ranked.csv",
    )
    result.add_argument(
        "--report-output",
        type=Path,
        default=ROOT / "eval" / "prompt_optimization" / "datasets" / "data_ranked_report.json",
    )
    result.add_argument(
        "--exclude-dirs",
        nargs="*",
        default=["_vendored", "externals", "tests", "__pycache__"],
        help="Directory names skipped while discovering Python files",
    )
    return result


def _row(info: FunctionInfo, rank: int, split: str) -> dict:
    return {
        "rank": rank,
        "split": split,
        "project": info.project,
        "source_file": info.source_file,
        "symbol": info.symbol,
        "branches": info.branches,
        "statements": info.statements,
        "lines": info.lines,
        "lineno": info.lineno,
    }


def main() -> int:
    args = parser().parse_args()
    if min(args.train_limit, args.validation_limit, args.test_limit) < 1:
        parser().error("all limits must be at least 1")

    projects = [
        (name, args.projects_root / name / name)
        for name in args.projects
    ]
    for name, package_dir in projects:
        if not package_dir.is_dir():
            parser().error(f"Package directory does not exist: {package_dir}")

    exclude_dirs = frozenset(args.exclude_dirs)
    targets, ranked = build_dataset(
        projects,
        train_limit=args.train_limit,
        validation_limit=args.validation_limit,
        test_limit=args.test_limit,
        exclude_dirs=exclude_dirs,
    )

    selected = len(targets)
    split_by_identity = {
        (row["project"], row["source_file"], row["symbol"]): row["split"]
        for row in targets
    }
    split_of = {
        info: split_by_identity.get(
            (info.project, info.source_file, info.symbol), "unselected"
        )
        for info in ranked
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in targets),
        encoding="utf-8",
    )

    with args.ranked_output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "rank",
                "split",
                "project",
                "source_file",
                "symbol",
                "branches",
                "statements",
                "lines",
                "lineno",
            ],
        )
        writer.writeheader()
        for index, info in enumerate(ranked, start=1):
            writer.writerow(_row(info, index, split_of[info]))

    per_project = Counter(info.project for info in ranked)
    splits = Counter(row["split"] for row in targets)
    project_splits = {
        name: dict(sorted(Counter(
            row["split"] for row in targets if row["project"] == name
        ).items()))
        for name in args.projects
    }
    report = {
        "train_limit": args.train_limit,
        "validation_limit": args.validation_limit,
        "test_limit": args.test_limit,
        "selected_total": selected,
        "projects": {
            name: {
                "functions": per_project[name],
                "selected_splits": project_splits[name],
            }
            for name in args.projects
        },
        "excluded_dirs": sorted(exclude_dirs),
        "splits": dict(sorted(splits.items())),
        "outputs": {
            "dataset": str(args.output),
            "ranked": str(args.ranked_output),
            "report": str(args.report_output),
        },
    }
    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Ranked {len(ranked)} functions across {', '.join(args.projects)}.")
    for name in args.projects:
        print(f"  {name}: {per_project[name]} functions")
    print(f"Selected {selected} = train {splits['train']} + "
          f"validation {splits['validation']} + test {splits['test']}.")
    print("\nTop 15 ranked functions:")
    print(f"{'rank':>4}  {'split':<11} {'project':<8} {'source_file':<45} "
          f"{'symbol':<42} {'br':>3} {'st':>3} {'ln':>3}")
    for index, info in enumerate(ranked[:15], start=1):
        print(f"{index:>4}  {split_of[info]:<11} {info.project:<8} "
              f"{info.source_file:<45} {info.symbol:<42} "
              f"{info.branches:>3} {info.statements:>3} {info.lines:>3}")
    print(f"\nWrote {args.output}")
    print(f"Wrote {args.ranked_output}")
    print(f"Wrote {args.report_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
