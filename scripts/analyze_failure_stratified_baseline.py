"""Summarize E70 train/validation baseline labels without opening holdout."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.optimization.failure_dataset import analyze_observed_failures  # noqa: E402


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "binh" / "e70_failure_stratified_32_manifest.json",
    )
    result.add_argument(
        "--artifacts-dir",
        type=Path,
        default=ROOT / "binh" / "phase1_runs" / "e70_baseline_labeling_r1",
    )
    result.add_argument(
        "--output",
        type=Path,
        default=ROOT / "binh" / "e70_baseline_labeling_summary.json",
    )
    return result


def main() -> int:
    args = parser().parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    batch_paths = sorted(args.artifacts_dir.glob("candidates/evaluations/**/batch.json"))
    batches = [json.loads(path.read_text(encoding="utf-8")) for path in batch_paths]
    if not batches:
        parser().error(f"No baseline batch files found under {args.artifacts_dir}")
    summary = analyze_observed_failures(manifest, batches)
    args.output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {args.output}")
    print(f"Targets: {summary['target_count']}")
    print(f"Aggregate score: {summary['overall']['score']:.4f}")
    print(f"Zero-score targets: {summary['headroom']['zero_score_target_count']}")
    print(f"Holdout analyzed: {summary['holdout_analyzed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
