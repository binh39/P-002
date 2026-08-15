"""Build and freeze the E70 static failure-stratified benchmark."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.optimization.failure_dataset import (  # noqa: E402
    build_failure_stratified_dataset,
    dataset_bytes,
    dataset_digest,
    load_dataset_identities,
)

DEFAULT_EXCLUSIONS = (
    ROOT / "binh" / "phase1_control_12.jsonl",
    ROOT / "binh" / "phase1_ablation_16.jsonl",
    ROOT / "binh" / "phase1_ablation_16_v2.jsonl",
    ROOT / "binh" / "phase1_stratified_24.jsonl",
)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Build E70 with static failure strata and a fresh locked holdout"
    )
    result.add_argument("--projects-root", type=Path, default=ROOT / "src" / "sample_repo")
    result.add_argument(
        "--projects",
        nargs="+",
        default=["isort", "mimesis", "mlxtend", "typesystem"],
    )
    result.add_argument("--train-per-project", type=int, default=4)
    result.add_argument("--validation-per-project", type=int, default=2)
    result.add_argument("--test-per-project", type=int, default=2)
    result.add_argument(
        "--exclude-dataset",
        type=Path,
        action="append",
        dest="exclude_datasets",
        help="Existing JSONL whose identities and structural duplicates must be excluded",
    )
    result.add_argument(
        "--output",
        type=Path,
        default=ROOT / "binh" / "e70_failure_stratified_32.jsonl",
    )
    result.add_argument(
        "--manifest-output",
        type=Path,
        default=ROOT / "binh" / "e70_failure_stratified_32_manifest.json",
    )
    return result


def main() -> int:
    args = parser().parse_args()
    exclusions = args.exclude_datasets or list(DEFAULT_EXCLUSIONS)
    missing = [path for path in exclusions if not path.is_file()]
    if missing:
        parser().error(f"Exclusion dataset does not exist: {missing[0]}")
    projects = [(name, args.projects_root / name / name) for name in args.projects]
    for name, path in projects:
        if not path.is_dir():
            parser().error(f"Package directory does not exist for {name}: {path}")

    excluded_identities = load_dataset_identities(exclusions)
    rows, _profiles, audit = build_failure_stratified_dataset(
        projects,
        train_per_project=args.train_per_project,
        validation_per_project=args.validation_per_project,
        test_per_project=args.test_per_project,
        excluded_identities=excluded_identities,
    )
    payload = dataset_bytes(rows)
    exclusion_records = [
        {
            "path": str(path.relative_to(ROOT)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in exclusions
    ]
    manifest = {
        "schema_version": 1,
        "kind": "failure_stratified_benchmark",
        "experiment": "E70",
        "created_on": date.today().isoformat(),
        "status": "frozen_before_evaluation",
        "selection_policy": "static_failure_stratified_v1",
        "selection_policy_digest": hashlib.sha256(
            b"static_failure_stratified_v1|test-first|project-balanced|structural-dedup"
        ).hexdigest(),
        "dataset_path": str(args.output.relative_to(ROOT)),
        "dataset_sha256": hashlib.sha256(payload).hexdigest(),
        "split_sha256": {
            split: dataset_digest(rows, split)
            for split in ("train", "validation", "test")
        },
        "holdout": {
            "split": "test",
            "status": "locked_unevaluated",
            "target_count": sum(row["split"] == "test" for row in rows),
            "access_rule": (
                "No model generation, coverage evaluation, prompt selection, or policy tuning "
                "may use this split before a candidate is frozen in a commit."
            ),
            "previous_e67_holdout_excluded": True,
        },
        "model_calls_during_selection": 0,
        "quotas_per_project": {
            "train": args.train_per_project,
            "validation": args.validation_per_project,
            "test": args.test_per_project,
        },
        "excluded_datasets": exclusion_records,
        "git_commit_at_generation": _git_commit(),
        "audit": audit,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)
    args.manifest_output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {len(rows)} targets to {args.output}")
    print(f"Dataset SHA-256: {manifest['dataset_sha256']}")
    print(f"Locked holdout SHA-256: {manifest['split_sha256']['test']}")
    print(f"Split counts: {dict(Counter(row['split'] for row in rows))}")
    print("Model calls during selection: 0")
    return 0


def _git_commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())
