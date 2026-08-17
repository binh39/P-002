"""Build a branch-ranked isort dataset split by a deterministic seed.

Selected ``--functions`` most-branch-heavy isort functions are allocated in
seeded difficulty strata and split into train / validation / test at 50 / 25 /
25. The larger train split gives GEPA enough contrasting failures to reflect
on, while the smaller validation split makes each search proposal affordable.
This is the dataset the ``optimize`` experiment reads:

    python scripts/build_my_isort_dataset.py --functions 160

The seed keeps the split reproducible: every run with the same function count
and seed produces the exact same assignment, so the locked test split is only
ever "opened" once per experiment configuration.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
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
TRAIN_RATIO = 0.50
VALIDATION_RATIO = 0.25
TEST_RATIO = 0.25
SPLITS = ("train", "validation", "test")


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
    result.add_argument(
        "--stratum-size",
        type=int,
        default=4,
        help=(
            "Adjacent difficulty-ranked targets per allocation stratum "
            "(default: 4, matching the 50/25/25 ratio)"
        ),
    )
    return result


def _split_counts(total: int) -> dict[str, int]:
    train = round(total * TRAIN_RATIO)
    validation = round(total * VALIDATION_RATIO)
    counts = {
        "train": train,
        "validation": validation,
        "test": total - train - validation,
    }
    # Preserve the public contract that every valid dataset has all three
    # splits, including the smallest supported total of three targets.
    for split in SPLITS:
        if counts[split] > 0:
            continue
        donor = max(SPLITS, key=lambda name: counts[name])
        counts[donor] -= 1
        counts[split] += 1
    return counts


def stratified_split_names(
    total: int, *, seed: int, stratum_size: int = 4,
) -> list[str]:
    """Allocate adjacent difficulty ranks proportionally across every split."""
    if total < 3:
        raise ValueError("total must be at least 3")
    if stratum_size < 1:
        raise ValueError("stratum_size must be at least 1")
    remaining = _split_counts(total)
    rng = random.Random(seed)
    assignments: list[str] = []
    while len(assignments) < total:
        size = min(stratum_size, total - len(assignments))
        remaining_total = sum(remaining.values())
        ideals = {
            split: size * remaining[split] / remaining_total for split in SPLITS
        }
        allocation = {
            split: min(remaining[split], int(ideals[split])) for split in SPLITS
        }
        unallocated = size - sum(allocation.values())
        tie_breakers = {split: rng.random() for split in SPLITS}
        priority = sorted(
            SPLITS,
            key=lambda split: (
                -(ideals[split] - allocation[split]),
                tie_breakers[split],
            ),
        )
        while unallocated:
            for split in priority:
                if allocation[split] >= remaining[split]:
                    continue
                allocation[split] += 1
                unallocated -= 1
                if not unallocated:
                    break
        labels = [
            split for split in SPLITS for _ in range(allocation[split])
        ]
        rng.shuffle(labels)
        assignments.extend(labels)
        for split in SPLITS:
            remaining[split] -= allocation[split]
    if any(remaining.values()):  # pragma: no cover - defensive invariant
        raise RuntimeError(f"Split allocation did not consume quotas: {remaining}")
    return assignments


def balanced_stratified_split_names(
    branches: list[int],
    statements: list[int],
    *,
    seed: int,
    stratum_size: int = 4,
    trials: int = 2_000,
) -> list[str]:
    """Choose a seeded stratified allocation with balanced per-target difficulty."""
    if len(branches) != len(statements):
        raise ValueError("branches and statements must have the same length")
    if not branches:
        raise ValueError("difficulty inputs cannot be empty")

    def imbalance(assignments: list[str]) -> float:
        score = 0.0
        for values in (branches, statements):
            means = [
                statistics.fmean(
                    value
                    for value, assigned in zip(values, assignments, strict=True)
                    if assigned == split
                )
                for split in SPLITS
            ]
            overall = statistics.fmean(means)
            score += statistics.pstdev(means) / overall if overall else 0.0
        return score

    best: tuple[float, list[str]] | None = None
    for trial in range(max(1, trials)):
        assignments = stratified_split_names(
            len(branches),
            seed=seed + trial * 1_000_003,
            stratum_size=stratum_size,
        )
        candidate = (imbalance(assignments), assignments)
        if best is None or candidate[0] < best[0]:
            best = candidate
    assert best is not None
    return best[1]


def main() -> int:
    args = parser().parse_args()
    if args.functions < 3:
        parser().error("--functions must be at least 3 to fill every split")
    if args.stratum_size < 1:
        parser().error("--stratum-size must be at least 1")

    functions = collect_project_functions(ISORT_PACKAGE, "isort")
    ranked = rank_functions(functions)
    total_available = len(ranked)
    if args.functions > total_available:
        parser().error(
            f"Only {total_available} isort functions found but --functions "
            f"{args.functions} was requested"
        )

    selected = ranked[: args.functions]
    split_names = balanced_stratified_split_names(
        [info.branches for info in selected],
        [info.statements for info in selected],
        seed=args.seed,
        stratum_size=args.stratum_size,
    )
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
        for info, split in zip(selected, split_names, strict=True)
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
    for split in SPLITS:
        split_rows = [row for row in rows if row["split"] == split]
        mean_branches = sum(row["branches"] for row in split_rows) / len(split_rows)
        mean_statements = sum(row["statements"] for row in split_rows) / len(split_rows)
        print(
            f"  {split:<10} mean branches={mean_branches:.2f}, "
            f"mean statements={mean_statements:.2f}"
        )
    print("Top branch-heavy selected:")
    print(f"{'split':<11}{'branches':>8}{'statements':>11}{'source_file':<45} symbol")
    top_rows = sorted(
        rows,
        key=lambda row: (
            -row["branches"], -row["statements"], row["source_file"], row["symbol"]
        ),
    )[:10]
    for row in top_rows:
        print(
            f"{row['split']:<11}{row['branches']:>8}{row['statements']:>11}"
            f" {row['source_file']:<45} {row['symbol']}"
        )
    print(f"\nWrote {args.functions} targets -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
