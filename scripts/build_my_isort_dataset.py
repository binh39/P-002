"""Build a branch-ranked isort dataset split by a deterministic seed.

Selected ``--functions`` most-branch-heavy isort functions are shuffled with a
fixed seed and split into train / validation / test at 20 / 40 / 40.  This is
the dataset the ``optimize`` experiment reads:

    python scripts/build_my_isort_dataset.py --functions 160

The seed keeps the split reproducible: every run with the same function count
and seed produces the exact same assignment, so the locked test split is only
ever "opened" once per experiment configuration.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.optimization.dataset_builder import (  # noqa: E402
    collect_project_functions,
    rank_functions,
)

ISORT_PACKAGE = ROOT / "src" / "sample_repo" / "isort" / "isort"
TRAIN_RATIO = 0.20
VALIDATION_RATIO = 0.40
TEST_RATIO = 0.40


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Build a seeded branch-ranked isort train/validation/test dataset"
    )
    result.add_argument(
        "--functions",
        type=int,
        default=160,
        help="Number of most-branch-heavy isort functions to select (default: 160)",
    )
    result.add_argument(
        "--seed",
        type=int,
        default=115,
        help="Deterministic shuffle seed for the train/valid/test split (default: 115)",
    )
    result.add_argument(
        "--output",
        type=Path,
        default=ROOT / "binh" / "isort_my_dataset.jsonl",
        help="Output JSONL dataset path",
    )
    return result


def main() -> int:
    args = parser().parse_args()
    if args.functions < 3:
        parser().error("--functions must be at least 3 to fill every split")

    functions = collect_project_functions(ISORT_PACKAGE, "isort")
    ranked = rank_functions(functions)
    total_available = len(ranked)
    if args.functions > total_available:
        parser().error(
            f"Only {total_available} isort functions found but --functions "
            f"{args.functions} was requested"
        )

    selected = ranked[: args.functions]
    rng = random.Random(args.seed)
    order = list(selected)
    rng.shuffle(order)

    n_train = round(args.functions * TRAIN_RATIO)
    n_validation = round(args.functions * VALIDATION_RATIO)
    # Validation rounds down, test absorbs the remainder so the three always sum
    # to the exact requested count.
    n_test = args.functions - n_train - n_validation

    split_names = ["train"] * n_train + ["validation"] * n_validation + ["test"] * n_test
    rows = [
        {
            "project": info.project,
            "source_file": info.source_file,
            "symbol": info.symbol,
            "branches": info.branches,
            "statements": info.statements,
            "lines": info.lines,
            "split": split,
        }
        for info, split in zip(order, split_names, strict=True)
    ]
    # Keep each split's rows sorted by branch count (descending) for readability.
    rows.sort(
        key=lambda row: (
            row["split"],
            -row["branches"],
            -row["statements"],
            row["source_file"],
            row["symbol"],
        )
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )

    by_split = Counter(row["split"] for row in rows)
    print(f"isort: {total_available} functions found; selected {args.functions} most branch-heavy")
    print(f"seed={args.seed}  train={by_split['train']} "
          f"validation={by_split['validation']} test={by_split['test']}")
    print("Top branch-heavy selected:")
    print(f"{'split':<11}{'branches':>8}{'statements':>11}{'source_file':<45} symbol")
    for row in rows[:10]:
        print(
            f"{row['split']:<11}{row['branches']:>8}{row['statements']:>11}"
            f" {row['source_file']:<45} {row['symbol']}"
        )
    print(f"\nWrote {args.functions} targets -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
