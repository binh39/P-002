from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .archive import (
    _estimated_aggregate,
    _materialize_candidate_test_archive,
    _target_estimated_score,
    collect_archive_candidates,
)
from .gepa import bundle_digest, evaluate_bundle_batch_cached, validate_bundle
from .models import SymbolTarget
from .prompts import PromptBundle
from .runner import CoverUpExperimentRunner

LiveStage = tuple[Path, int]


def _policy_digest(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _load_live_stages(stages: list[LiveStage]) -> list[dict[str, Any]]:
    if not stages:
        raise ValueError("Live sequential archive requires at least one prompt stage")
    loaded = []
    seen: set[tuple[str, int]] = set()
    for prompt_path, replicate in stages:
        if replicate < 0:
            raise ValueError("Live sequential archive replicate must be non-negative")
        prompt_path = prompt_path.resolve()
        bundle = PromptBundle.load(prompt_path)
        if error := validate_bundle(bundle):
            raise ValueError(f"Invalid live stage prompt {prompt_path}: {error}")
        digest = bundle_digest(bundle)
        key = digest, replicate
        if key in seen:
            raise ValueError(f"Duplicate live sequential stage {digest}:{replicate}")
        seen.add(key)
        loaded.append({
            "prompt_path": prompt_path,
            "prompt_sha256": hashlib.sha256(prompt_path.read_bytes()).hexdigest(),
            "prompt_digest": digest,
            "replicate": replicate,
            "bundle": bundle,
        })
    return loaded


def run_live_sequential_archive(
    *,
    runner: CoverUpExperimentRunner,
    targets: list[SymbolTarget],
    stages: list[LiveStage],
    output_dir: Path,
    sample_repos_dir: Path,
    split: str,
    target_stop_score: float = 0.80,
    cohort_stage_count: int | None = None,
    allow_holdout: bool = False,
) -> dict[str, Any]:
    """Generate only unresolved targets at each frozen prompt/replicate stage."""
    if not targets:
        raise ValueError("Live sequential archive requires at least one target")
    if {target.split for target in targets} != {split}:
        raise ValueError("Live sequential targets must all match the requested split")
    if split == "test" and not allow_holdout:
        raise ValueError("The test split is locked; pass allow_holdout for the one-shot run")
    if not 0.0 < target_stop_score <= 1.0:
        raise ValueError("Live sequential target_stop_score must be in (0, 1]")
    loaded_stages = _load_live_stages(stages)
    if cohort_stage_count is None:
        cohort_stage_count = len(loaded_stages)
    if cohort_stage_count < len(loaded_stages):
        raise ValueError("cohort_stage_count cannot be smaller than the frozen stage count")

    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"Archive output already exists: {output_dir}")
    artifacts_dir = runner.config.artifacts_dir.resolve()
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    candidate_dir = artifacts_dir / "candidates"
    payload = {
        "schema_version": 1,
        "kind": "live_sequential_archive_policy",
        "split": split,
        "target_stop_score": target_stop_score,
        "cohort_stage_count": cohort_stage_count,
        "coverup_model": runner.config.coverup_model,
        "max_attempts": runner.config.max_attempts,
        "repeat_tests": runner.config.repeat_tests,
        "targets": [target.__dict__ for target in targets],
        "stages": [
            {
                "prompt_path": str(stage["prompt_path"]),
                "prompt_sha256": stage["prompt_sha256"],
                "prompt_digest": stage["prompt_digest"],
                "replicate": stage["replicate"],
            }
            for stage in loaded_stages
        ],
    }
    policy_digest = _policy_digest(payload)
    state_path = artifacts_dir / "sequential_holdout_state.json"
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("policy_digest") != policy_digest:
            raise RuntimeError(
                "A different sequential holdout policy already started in this artifacts directory"
            )
    else:
        state = {
            **payload,
            "policy_digest": policy_digest,
            "status": "started",
            "completed_stages": [],
        }
        state_path.write_text(
            json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    identities = {
        (target.project, target.source_file, target.symbol, target.split): target
        for target in targets
    }
    denominators: dict = {}
    covered: set = set()
    selected_batches = []
    stage_rows = []
    target_generation_calls = 0
    baseline_digest = loaded_stages[0]["prompt_digest"]
    for index, stage in enumerate(loaded_stages):
        eligible_identities = (
            set(identities)
            if index == 0
            else {
                identity
                for identity in identities
                if _target_estimated_score(identity, covered, denominators)
                < target_stop_score
            }
        )
        if not eligible_identities:
            break
        eligible_targets = [
            target
            for identity, target in identities.items()
            if identity in eligible_identities
        ]
        workspace_kind = (
            "baseline" if stage["prompt_digest"] == baseline_digest else "candidate"
        )
        batch = evaluate_bundle_batch_cached(
            runner,
            eligible_targets,
            stage["bundle"],
            candidate_dir,
            split=split,
            workspace_kind=workspace_kind,
            replicate=stage["replicate"],
        )
        stage_candidates, stage_denominators = collect_archive_candidates(
            artifacts_dir, [batch]
        )
        if index == 0:
            denominators = stage_denominators
            missing = set(identities) - set(denominators)
            if missing:
                raise RuntimeError(
                    "Baseline holdout stage is missing coverage denominators for "
                    f"{len(missing)} target(s)"
                )
        else:
            for identity, denominator in stage_denominators.items():
                if denominators.get(identity) != denominator:
                    raise RuntimeError(
                        "Holdout coverage denominator changed for "
                        f"{identity[1]}::{identity[2]}"
                    )
        before = set(covered)
        for candidate in stage_candidates:
            covered.update(candidate["units"])
        marginal = covered - before
        target_generation_calls += len(eligible_targets)
        selected_batches.append(batch)
        aggregate = _estimated_aggregate(covered, denominators)
        stage_row = {
            "stage": index,
            "prompt_digest": stage["prompt_digest"],
            "replicate": stage["replicate"],
            "evaluation_digest": batch.get("evaluation_digest"),
            "eligible_target_count": len(eligible_targets),
            "eligible_targets": [target.__dict__ for target in eligible_targets],
            "candidate_test_count": len(stage_candidates),
            "marginal_coverage_units": len(marginal),
            "estimated_aggregate_score": aggregate["score"],
            "targets_at_stop_score": sum(
                _target_estimated_score(identity, covered, denominators)
                >= target_stop_score
                for identity in identities
            ),
            "run_ids": batch.get("run_ids", []),
        }
        stage_rows.append(stage_row)
        state["completed_stages"] = stage_rows
        state_path.write_text(
            json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    requested_calls = len(loaded_stages) * len(targets)
    cohort_calls = cohort_stage_count * len(targets)
    policy = {
        "kind": "cost_aware_sequential_live",
        "policy_digest": policy_digest,
        "target_stop_score": target_stop_score,
        "stages_requested": payload["stages"],
        "stages_executed": stage_rows,
        "target_count": len(targets),
        "target_generation_calls": target_generation_calls,
        "exhaustive_target_generation_calls": requested_calls,
        "cohort_exhaustive_target_generation_calls": cohort_calls,
        "target_generation_savings": 1.0 - target_generation_calls / requested_calls,
        "cohort_target_generation_savings": 1.0 - target_generation_calls / cohort_calls,
        "cost_proxy_meaning": (
            "One target generation at one prompt/replicate stage; provider retries and tokens are not included"
        ),
        "estimated_aggregate": _estimated_aggregate(covered, denominators),
    }
    report = _materialize_candidate_test_archive(
        project_root=runner.config.project_root.resolve(),
        artifacts_dir=artifacts_dir,
        output_dir=output_dir,
        sample_repos_dir=sample_repos_dir.resolve(),
        split=split,
        selected_digest=policy_digest[:12],
        batches=selected_batches,
        comparison_batches=[selected_batches[0]],
        pytest_args=runner.config.pytest_args,
        repeat_tests=runner.config.repeat_tests,
        report_metadata={
            "source_replicates": sorted({stage["replicate"] for stage in loaded_stages}),
            "sequential_policy": policy,
            "live_evaluation": {
                "coverup_model": runner.config.coverup_model,
                "max_attempts": runner.config.max_attempts,
                "artifacts_dir": str(artifacts_dir),
                "one_shot_holdout": split == "test",
            },
        },
    )
    state["status"] = "completed"
    state["report"] = str(output_dir / "candidate_test_archive.json")
    state_path.write_text(
        json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return report
