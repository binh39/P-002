from __future__ import annotations

import ast
import hashlib
import json
import os
import random
import re
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import gepa as gepa_core
from gepa.strategies.candidate_selector import (
    CurrentBestCandidateSelector,
    ParetoCandidateSelector,
)

from .metrics import (
    BRANCH_SCORE_WEIGHT,
    STATEMENT_SCORE_WEIGHT,
    aggregate_coverage_score,
)
from .models import SymbolTarget
from .prompts import PromptBundle
from .runner import CoverUpExperimentRunner

INITIAL_PLACEHOLDERS = ("{filename}", "{coverage_targets}", "{source_excerpt}")
ERROR_PLACEHOLDERS = ("{error}",)
COMPONENT_PLACEHOLDERS = {
    "initial": INITIAL_PLACEHOLDERS,
    "error": ERROR_PLACEHOLDERS,
}
COMPONENT_ROLES = {
    "initial": (
        "Generate the first complete pytest module from source and missing coverage "
        "using an explicit Reflexion-style observe-plan-act-check procedure."
    ),
    "error": (
        "Reflect on execution or collection feedback, identify the concrete failed "
        "assumption, and repair the complete pytest module without losing useful behavior."
    ),
}
MIN_COMPONENT_CHAR_BUDGET = {"initial": 2_400, "error": 1_600}
UPDATE_PROMPT_COMPONENT_TOOL = {
    "type": "function",
    "function": {
        "name": "update_prompt_component",
        "description": (
            "Select initial, error, or all and return complete replacement "
            "templates in the same call. Replacements must give a less-capable "
            "test model a detailed Reflexion procedure and an unambiguous reflection/code "
            "output contract. The all selection is always allowed."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "component": {
                    "type": "string",
                    "enum": ["initial", "error", "all"],
                },
                "replacements": {
                    "type": "object",
                    "properties": {
                        "initial": {"type": "string"},
                        "error": {"type": "string"},
                    },
                    "additionalProperties": False,
                },
                "diagnosis": {"type": "string"},
                "evidence": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                },
                "successful_experiment_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                },
            },
            "required": [
                "component",
                "replacements",
                "diagnosis",
                "evidence",
                "successful_experiment_ids",
            ],
            "additionalProperties": False,
        },
    },
}
RUN_TEST_EXPERIMENT_TOOL = {
    "type": "function",
    "function": {
        "name": "run_test_experiment",
        "description": (
            "Run one complete optimizer-authored pytest module against a failed "
            "coverage case. The module is diagnostic teacher evidence only."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "case_id": {"type": "string"},
                "test_module": {
                    "type": "string",
                    "description": "A complete executable pytest module.",
                },
                "hypothesis": {
                    "type": "string",
                    "description": (
                        "The concrete causal change this test makes relative to the failed generated test."
                    ),
                },
            },
            "required": ["case_id", "test_module", "hypothesis"],
            "additionalProperties": False,
        },
    },
}
AUTO_METRIC_BUDGETS = {"light": 120, "medium": 300, "heavy": 600}
REFLECTION_REQUEST_BEGIN = "PROMPTOPT_REFLECTION_REQUEST_BEGIN"
REFLECTION_REQUEST_END = "PROMPTOPT_REFLECTION_REQUEST_END"
FULL_LOG_BEGIN = "PROMPTOPT_DEV_FULL_LOG_BEGIN"
FULL_LOG_END = "PROMPTOPT_DEV_FULL_LOG_END"
MAX_OPTIMIZER_TEST_EXPERIMENTS = 5
REFLECTION_MINIBATCH_SIZE = 5
PERFECT_COVERAGE_THRESHOLD = 1.0 - 1e-6

_DIGEST_LOCKS: dict[str, threading.Lock] = {}
_DIGEST_LOCKS_GUARD = threading.Lock()


class BestParetoCandidateSelector:
    """Select the aggregate best candidate 70% of the time, Pareto otherwise."""

    def __init__(
        self,
        *,
        best_probability: float = 0.7,
        rng: random.Random | None = None,
    ) -> None:
        if not 0.0 <= best_probability <= 1.0:
            raise ValueError("best_probability must be between 0 and 1")
        self.best_probability = best_probability
        self.rng = rng or random.Random(0)
        self.best_selector = CurrentBestCandidateSelector()
        self.pareto_selector = ParetoCandidateSelector(self.rng)

    def select_candidate_idx(self, state: Any) -> int:
        selector = self.best_selector if self.rng.random() < self.best_probability else self.pareto_selector
        return selector.select_candidate_idx(state)


def log_reflection_request(request: Mapping[str, Any]) -> None:
    """Print the exact native-tool request sent to the optimization model."""
    print(REFLECTION_REQUEST_BEGIN, flush=True)
    print(json.dumps(request, indent=2, ensure_ascii=False), flush=True)
    print(REFLECTION_REQUEST_END, flush=True)


def _full_reflection_logs_enabled() -> bool:
    return os.environ.get("PROMPTOPT_FULL_REFLECTION_LOGS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _log_value(value: Any) -> Any:
    """Convert SDK response objects to JSON-compatible diagnostic output."""
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Mapping):
        return {str(key): _log_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_log_value(item) for item in value]
    for method_name in ("model_dump", "to_dict"):
        method = getattr(value, method_name, None)
        if callable(method):
            try:
                return _log_value(method())
            except (TypeError, ValueError):
                pass
    attributes = getattr(value, "__dict__", None)
    if isinstance(attributes, dict):
        return _log_value(attributes)
    return str(value)


def log_full_reflection_event(event: str, payload: Any) -> None:
    """Emit full dev diagnostics to stdout; Cloud Logging captures the stream."""
    if not _full_reflection_logs_enabled():
        return
    print(FULL_LOG_BEGIN, flush=True)
    print(
        json.dumps(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "event": event,
                "payload": _log_value(payload),
            },
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        flush=True,
    )
    print(FULL_LOG_END, flush=True)


def _digest_lock(key: str) -> threading.Lock:
    """Return the process-local lock that serializes one cached evaluation."""
    with _DIGEST_LOCKS_GUARD:
        return _DIGEST_LOCKS.setdefault(key, threading.Lock())


def validate_template(
    template: str,
    required_placeholders: tuple[str, ...] = INITIAL_PLACEHOLDERS,
) -> str | None:
    missing = [placeholder for placeholder in required_placeholders if placeholder not in template]
    if missing:
        return f"Candidate omitted required literal placeholders: {missing}."
    try:
        template.format(
            filename="x.py",
            coverage_targets="line 1",
            source_excerpt="def f(): pass",
            error="pytest failed",
        )
    except (KeyError, ValueError) as exc:
        return f"Candidate is not a valid format template: {exc}."
    return None


def validate_bundle(bundle: PromptBundle) -> str | None:
    templates = (
        ("initial", bundle.initial, INITIAL_PLACEHOLDERS),
        ("error", bundle.error or "", ERROR_PLACEHOLDERS),
    )
    for name, template, placeholders in templates:
        if error := validate_template(template, placeholders):
            return f"Invalid {name} prompt: {error}"
    return None


def bundle_digest(bundle: PromptBundle) -> str:
    serialized = "\n---PROMPT---\n".join((bundle.initial, bundle.error or ""))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def _cache_name(workspace_kind: str, replicate: int) -> str:
    stem = "baseline_batch" if workspace_kind == "baseline" else "batch"
    return f"{stem}.json" if replicate == 0 else f"{stem}_r{replicate}.json"


def _evaluation_digest(
    runner: CoverUpExperimentRunner,
    targets: list[SymbolTarget],
) -> str:
    """Fingerprint every input that can change a cached prompt evaluation."""
    config = getattr(runner, "config", None)
    config_values = {
        name: str(getattr(config, name, ""))
        for name in (
            "coverup_model",
            "max_attempts",
            "repeat_tests",
            "pytest_args",
            "max_concurrency",
            "rate_limit",
        )
    }
    source_hashes = {}
    environment_fingerprints = {}
    if config is not None:
        project_root = Path(getattr(config, "project_root", ".")).resolve()
        resolve_package = getattr(config, "package_dir_for", None)
        for target in targets:
            if resolve_package is not None:
                package_dir = Path(resolve_package(target.project)).resolve()
            else:
                package_dir = Path(getattr(config, "package_dir", ".")).resolve()
            source = Path(target.source_file)
            candidates = (
                package_dir.parent / source,
                package_dir / source,
                project_root / source,
                package_dir / source.name,
            )
            path = next((value for value in candidates if value.is_file()), None)
            if path is not None:
                source_hashes[target.source_file] = hashlib.sha256(path.read_bytes()).hexdigest()
    fingerprint_resolver = getattr(runner, "environment_fingerprints", None)
    if callable(fingerprint_resolver):
        environment_fingerprints = fingerprint_resolver(targets)
    payload = {
        # Schema 10 fixed PYTHONHASHSEED across CoverUp and coverage subprocesses.
        # Schema 11 makes repeat_tests effective during generation and final
        # scoring. Schema 12 preserves denominators from pytest exit 1 while
        # assigning failing generated suites zero covered units. Schema 13
        # batches CoverUp generation and scores only each target's traced tests.
        # Schema 14 restores isolated per-target CoverUp processes in one bounded
        # pool, consolidates traced tests, and skips redundant final-suite coverage.
        # Schema 15 binds every cached evaluation to immutable per-project
        # sandbox environment fingerprints.
        "cache_schema": 15,
        "config": config_values,
        "targets": [_target_identity(target) for target in targets],
        "sources": source_hashes,
        "environment_fingerprints": environment_fingerprints,
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:12]


def evaluate_bundle_cached(
    runner: CoverUpExperimentRunner,
    target: SymbolTarget,
    bundle: PromptBundle,
    candidate_dir: Path,
    split_targets: list[SymbolTarget] | None = None,
    *,
    replicate: int = 0,
) -> dict:
    """Return one target result from a cached split-level batch evaluation."""
    batch = evaluate_bundle_batch_cached(
        runner,
        split_targets or [target],
        bundle,
        candidate_dir,
        split=target.split,
        replicate=replicate,
    )
    wanted = _target_identity(target)
    for result in batch["results"]:
        if _result_identity(result) == wanted:
            return result
    raise KeyError(f"Target {wanted!r} is absent from cached batch {batch.get('run_ids', [])}")


def evaluate_bundle_batch_cached(
    runner: CoverUpExperimentRunner,
    targets: list[SymbolTarget],
    bundle: PromptBundle,
    candidate_dir: Path,
    *,
    split: str | None = None,
    workspace_kind: str = "candidate",
    replicate: int = 0,
) -> dict:
    """Evaluate and cache one batch with isolated per-target coverage scores."""
    if not targets:
        raise ValueError("Batch evaluation requires at least one target")
    if replicate < 0:
        raise ValueError("replicate must be non-negative")
    target_splits = {target.split for target in targets}
    if split is None:
        if len(target_splits) != 1:
            raise ValueError(f"Batch targets must share one split, got {sorted(target_splits)}")
        split = next(iter(target_splits))
    elif target_splits != {split}:
        raise ValueError(f"Batch targets do not match requested split {split!r}: {sorted(target_splits)}")

    # GEPA may sample the same example more than once in a minibatch. Evaluate each
    # identity once so CoverUp does not generate duplicate tests or return ambiguous
    # per-target results inside the consolidated candidate workspace.
    unique_targets: list[SymbolTarget] = []
    seen_targets: set[tuple[str, str, str, str]] = set()
    for target in targets:
        identity = _target_identity(target)
        if identity not in seen_targets:
            seen_targets.add(identity)
            unique_targets.append(target)
    targets = unique_targets

    digest = bundle_digest(bundle)
    evaluation_digest = _evaluation_digest(runner, targets)
    lock_key = f"{digest}:{evaluation_digest}:{split}:{workspace_kind}:{replicate}"
    with _digest_lock(lock_key):
        candidate_dir.mkdir(parents=True, exist_ok=True)
        candidate = candidate_dir / f"{digest}.json"
        if not candidate.exists():
            bundle.save(candidate)

        safe_split = re.sub(r"[^A-Za-z0-9_.-]+", "_", split).strip("._-")
        if not safe_split:
            raise ValueError("split must contain at least one safe path character")
        cache_path = (
            candidate_dir
            / "evaluations"
            / digest
            / evaluation_digest
            / safe_split
            / _cache_name(workspace_kind, replicate)
        )
        if cache_path.exists():
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            requested = {_target_identity(target) for target in targets}
            cached_targets = {_result_identity(result) for result in cached.get("results", [])}
            if cached_targets != requested:
                raise RuntimeError(
                    f"Cached batch target set differs for candidate {digest} split {split!r}. "
                    "Use a fresh artifacts directory."
                )
            current_fingerprints = (
                runner.environment_fingerprints(targets)
                if hasattr(runner, "environment_fingerprints")
                else {}
            )
            if cached.get("environment_fingerprints", {}) != current_fingerprints:
                raise RuntimeError(
                    "Cached batch environment fingerprint differs from the active sandbox. "
                    "The baseline must be evaluated again under the new environment."
                )
            cached["aggregate"] = aggregate_coverage_score(cached.get("results", []))
            return cached

        run_candidate_id = f"{digest}-{evaluation_digest}"
        if replicate:
            run_candidate_id += f"-r{replicate}"
        # The runner evaluates each target in an isolated temporary CoverUp
        # workspace using a bounded global pool, then consolidates only tests
        # attributed by trace into one persistent candidate workspace. Each target
        # still gets a separate pytest/coverage pass and per-example feedback.
        records = [
            runner.evaluate_batch(
                targets,
                candidate,
                candidate_id=run_candidate_id,
                split=split,
                workspace_kind=workspace_kind,
            )
        ]

        results = []
        for record in records:
            if len(record.results) != len(targets):
                raise RuntimeError(
                    "Minibatch evaluation returned an unexpected result count: "
                    f"{len(record.results)} for {len(targets)} targets"
                )
            for target_result in record.results:
                target = target_result.target
                results.append(
                    {
                        "prompt_digest": digest,
                        "evaluation_digest": evaluation_digest,
                        "replicate": replicate,
                        "target": target.__dict__,
                        "run_id": record.run_id,
                        "score": (float(target_result.score["score"]) if target_result.score else 0.0),
                        "coverage": target_result.score,
                        "feedback": target_result.feedback,
                        "attempt_traces": getattr(target_result, "attempt_traces", []),
                        "environment_fingerprint": getattr(
                            target_result, "environment_fingerprint", None
                        ),
                    }
                )
        batch = {
            "prompt_digest": digest,
            "evaluation_digest": evaluation_digest,
            "replicate": replicate,
            "split": split,
            "workspace_kind": workspace_kind,
            "run_ids": [record.run_id for record in records],
            "generator_exit_codes": [int(getattr(record, "exit_code", 0) or 0) for record in records],
            "tests_workspaces": [record.tests_workspace for record in records],
            "environment_fingerprints": (
                runner.environment_fingerprints(targets)
                if hasattr(runner, "environment_fingerprints")
                else {}
            ),
            "results": results,
        }
        batch["aggregate"] = aggregate_coverage_score(results)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(batch, indent=2, ensure_ascii=False), encoding="utf-8")
        return batch


def _target_identity(target: SymbolTarget) -> tuple[str, str, str, str]:
    return target.project, target.source_file, target.symbol, target.split


def _result_identity(result: dict) -> tuple[str, str, str, str]:
    target = result["target"]
    return (target["project"], target["source_file"], target["symbol"], target["split"])


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _has_incomplete_coverage(record: Mapping[str, Any]) -> bool:
    """Return whether a measured target still has any uncovered behavior."""
    score = record.get("candidate_score", record.get("score"))
    if isinstance(score, int | float):
        return float(score) < PERFECT_COVERAGE_THRESHOLD
    coverage = record.get("coverage")
    if isinstance(coverage, Mapping):
        coverage_score = coverage.get("score")
        if isinstance(coverage_score, int | float):
            return float(coverage_score) < PERFECT_COVERAGE_THRESHOLD
    # Missing measurements must remain eligible so failures are not hidden.
    return True


def _clip_text(value: Any, limit: int, *, keep_tail: bool = False) -> str:
    text = str(value or "")
    if len(text) <= limit:
        return text
    marker = f"\n... [truncated {len(text) - limit} characters] ...\n"
    available = max(0, limit - len(marker))
    return marker + text[-available:] if keep_tail else text[:available] + marker


def _compact_attempt(attempt: Mapping[str, Any]) -> dict[str, Any]:
    """Keep one observable CoverUp action/result without raw transcript noise."""
    row = {
        key: attempt[key]
        for key in (
            "attempt",
            "replicate",
            "component",
            "outcome",
            "next_component",
            "finish_reason",
            "missing_imports",
            "gained_lines",
            "gained_branches",
            "remaining_lines",
            "remaining_branches",
        )
        if key in attempt
    }
    if "prompt_input" in attempt:
        row["prompt_input"] = _clip_text(attempt["prompt_input"], 6_000, keep_tail=True)
    if "generated_test" in attempt:
        row["generated_test"] = _clip_text(attempt["generated_test"], 10_000)
    if "model_reflection" in attempt:
        row["model_reflection"] = _clip_text(attempt["model_reflection"], 3_000)
    if "execution_error" in attempt:
        row["execution_error"] = _clip_text(attempt["execution_error"], 6_000, keep_tail=True)
    if "assistant_response" in attempt:
        row["assistant_response"] = _clip_text(attempt["assistant_response"], 3_000)
    get_info_calls = attempt.get("get_info_calls", [])
    if isinstance(get_info_calls, Sequence) and not isinstance(get_info_calls, str | bytes):
        row["get_info_calls"] = [
            {
                "name": str(call.get("name", "get_info")),
                "arguments": call.get("arguments", {}),
                "result": _clip_text(call.get("result", ""), 6_000),
            }
            for call in get_info_calls
            if isinstance(call, Mapping)
        ]
    return row


def _build_execution_episodes(
    attempts: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Reconstruct initial generation and every subsequent repair transition.

    Attempts are grouped by replicate.  Each error-stage attempt points back to
    the concrete failing test and execution error that caused that repair, so
    reflection sees the causal before/after sequence instead of disconnected
    component-local snippets.
    """
    grouped: dict[int, list[Mapping[str, Any]]] = {}
    for attempt in attempts:
        replicate = int(attempt.get("replicate", 0) or 0)
        grouped.setdefault(replicate, []).append(attempt)

    episodes: list[dict[str, Any]] = []
    for replicate, values in sorted(grouped.items()):
        initial_attempts: list[dict[str, Any]] = []
        repair_transitions: list[dict[str, Any]] = []
        previous_test_attempt: Mapping[str, Any] | None = None

        for attempt in values:
            component = attempt.get("component")
            if component == "initial":
                initial_attempts.append(_compact_attempt(attempt))
            elif component == "error":
                transition = {
                    "attempt": attempt.get("attempt"),
                    "replicate": replicate,
                    "failing_test": _clip_text(
                        (previous_test_attempt or {}).get("generated_test", ""),
                        10_000,
                    ),
                    "error": _clip_text(
                        (previous_test_attempt or {}).get("execution_error", ""),
                        6_000,
                        keep_tail=True,
                    ),
                    "repair_prompt_input": _clip_text(attempt.get("prompt_input", ""), 6_000, keep_tail=True),
                    "repaired_test": _clip_text(attempt.get("generated_test", ""), 10_000),
                    "model_reflection": _clip_text(attempt.get("model_reflection", ""), 3_000),
                    "outcome": attempt.get("outcome", "unknown"),
                    "get_info_calls": _compact_attempt(attempt).get("get_info_calls", []),
                }
                for key in (
                    "execution_error",
                    "finish_reason",
                    "missing_imports",
                    "gained_lines",
                    "gained_branches",
                    "remaining_lines",
                    "remaining_branches",
                ):
                    if key in attempt:
                        output_key = "execution_error_after" if key == "execution_error" else key
                        value = attempt[key]
                        transition[output_key] = (
                            _clip_text(value, 6_000, keep_tail=True) if key == "execution_error" else value
                        )
                repair_transitions.append(transition)

            if attempt.get("generated_test"):
                previous_test_attempt = attempt

        terminal = _compact_attempt(values[-1]) if values else {}
        episodes.append(
            {
                "replicate": replicate,
                "initial_attempts": initial_attempts,
                "repair_transitions": repair_transitions,
                "terminal_outcome": terminal.get("outcome", "unknown"),
                "terminal_component": terminal.get("component", "unknown"),
            }
        )
    return episodes


def _attempts_with_replicates(samples: Sequence[Mapping[str, Any]]) -> list[dict]:
    return [
        {**attempt, "replicate": replicate}
        for replicate, sample in enumerate(samples)
        for attempt in sample.get("attempt_traces", [])
    ]


def _representative_test(attempts: Sequence[Mapping[str, Any]]) -> str:
    for attempt in reversed(attempts):
        generated_test = attempt.get("generated_test")
        if generated_test:
            return _clip_text(generated_test, 12_000)
    return ""


def require_paired_environment_fingerprints(
    results: Sequence[Mapping[str, Any]],
    reference_results: Sequence[Mapping[str, Any]],
) -> None:
    """Reject paired scoring across different immutable project environments."""

    references = {_result_identity(dict(item)): item for item in reference_results}
    for result in results:
        identity = _result_identity(dict(result))
        reference = references.get(identity)
        if reference is None:
            continue
        current = result.get("environment_fingerprint")
        baseline = reference.get("environment_fingerprint")
        if current != baseline and (current is not None or baseline is not None):
            raise RuntimeError(
                "Environment fingerprint mismatch for paired baseline/candidate scoring: "
                f"{identity[0]}:{identity[1]}::{identity[2]} "
                f"baseline={baseline!r}, candidate={current!r}. "
                "Regenerate the baseline under the active project sandbox."
            )


def _comparison_outcome(score_delta: float, *, tolerance: float = 1e-9) -> str:
    if score_delta > tolerance:
        return "improved"
    if score_delta < -tolerance:
        return "regressed"
    return "tied"


def _exemplar_type(trajectory: Mapping[str, Any]) -> str:
    outcome = trajectory.get("comparison_outcome")
    if outcome == "regressed":
        return "regression"
    if outcome == "improved" or float(trajectory.get("score", 0.0)) >= 0.999999:
        return "positive"
    if float(trajectory.get("score", 0.0)) < 0.999999:
        return "failure"
    return "neutral"


def _order_contrastive_trajectories(
    trajectories: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    """Lead with one negative and one positive example when both are available."""
    values = list(trajectories)
    negative = [trajectory for trajectory in values if _exemplar_type(trajectory) in {"regression", "failure"}]
    positive = [trajectory for trajectory in values if _exemplar_type(trajectory) == "positive"]
    representatives: list[Mapping[str, Any]] = []
    if negative:
        representatives.append(
            min(
                negative,
                key=lambda trajectory: (
                    float(trajectory.get("score_delta", 0.0)),
                    float(trajectory.get("score", 0.0)),
                ),
            )
        )
    if positive:
        best_positive = max(
            positive,
            key=lambda trajectory: (
                float(trajectory.get("score_delta", 0.0)),
                float(trajectory.get("score", 0.0)),
            ),
        )
        if all(best_positive is not value for value in representatives):
            representatives.append(best_positive)
    return [
        *representatives,
        *(trajectory for trajectory in values if all(trajectory is not value for value in representatives)),
    ]


def evaluate_bundle_repeated(
    runner: CoverUpExperimentRunner,
    targets: list[SymbolTarget],
    bundle: PromptBundle,
    candidate_dir: Path,
    *,
    split: str,
    workspace_kind: str = "candidate",
    replicates: int = 1,
    reference_results: list[dict] | None = None,
) -> dict:
    """Evaluate multiple independent generations and average their coverage scores."""
    if replicates < 1:
        raise ValueError("replicates must be at least 1")
    batches = [
        evaluate_bundle_batch_cached(
            runner,
            targets,
            bundle,
            candidate_dir,
            split=split,
            workspace_kind=workspace_kind,
            replicate=replicate,
        )
        for replicate in range(replicates)
    ]
    aggregate_rows = [
        (
            (
                require_paired_environment_fingerprints(batch["results"], reference_results)
                if reference_results is not None
                else None
            )
            or aggregate_coverage_score(
                batch["results"],
                reference_results=reference_results,
            )
        )
        for batch in batches
    ]
    aggregate_keys = {key for row in aggregate_rows for key, value in row.items() if isinstance(value, int | float)}
    aggregate = {
        key: _mean([float(row[key]) for row in aggregate_rows if key in row]) for key in sorted(aggregate_keys)
    }
    merged_results = []
    for target in targets:
        identity = _target_identity(target)
        samples = [result for batch in batches for result in batch["results"] if _result_identity(result) == identity]
        representative = dict(samples[0])
        representative["score"] = _mean([float(item["score"]) for item in samples])
        representative["replicate_scores"] = [float(item["score"]) for item in samples]
        coverages = [item.get("coverage") for item in samples if item.get("coverage")]
        if coverages:
            merged_coverage = dict(coverages[0])
            numeric_keys = (
                "score",
                "statement_gain",
                "branch_gain",
                "statement_coverage",
                "branch_coverage",
                "covered_statements",
                "num_statements",
                "covered_branches",
                "num_branches",
            )
            for key in numeric_keys:
                values = [float(coverage[key]) for coverage in coverages if key in coverage]
                if values:
                    merged_coverage[key] = _mean(values)
            merged_coverage["valid"] = all(coverage.get("valid") is not False for coverage in coverages)
            representative["coverage"] = merged_coverage
        representative["feedback"] = "\n\n".join(
            f"Replicate {index}:\n{item['feedback']}" for index, item in enumerate(samples)
        )
        merged_results.append(representative)
    return {
        "prompt_digest": bundle_digest(bundle),
        "split": split,
        "workspace_kind": workspace_kind,
        "replicates": replicates,
        "run_ids": [run_id for batch in batches for run_id in batch.get("run_ids", [])],
        "tests_workspaces": [workspace for batch in batches for workspace in batch.get("tests_workspaces", [])],
        "environment_fingerprints": {
            project: fingerprint
            for batch in batches
            for project, fingerprint in batch.get("environment_fingerprints", {}).items()
        },
        "results": merged_results,
        "aggregate": aggregate,
        "batches": batches,
    }


def _bundle_split_summary(batch: dict) -> dict[str, Any]:
    """Reduce one split-level evaluation batch to aggregate coverage numbers."""
    aggregate = batch.get("aggregate") or aggregate_coverage_score(batch["results"])
    return {
        "num_targets": len(batch["results"]),
        "score": float(aggregate.get("score", 0.0)),
        "statement_coverage": float(aggregate.get("statement_coverage", 0.0)),
        "branch_coverage": float(aggregate.get("branch_coverage", 0.0)),
        "covered_statements": int(aggregate.get("covered_statements", 0)),
        "num_statements": int(aggregate.get("num_statements", 0)),
        "covered_branches": int(aggregate.get("covered_branches", 0)),
        "num_branches": int(aggregate.get("num_branches", 0)),
    }


def build_coverage_report(
    runner: CoverUpExperimentRunner,
    targets_by_split: dict[str, list[SymbolTarget]],
    baseline: PromptBundle,
    optimized: PromptBundle,
    candidate_dir: Path,
    *,
    evaluation_replicates: int = 1,
) -> dict[str, Any]:
    """Aggregate statement/branch coverage per split for two prompt versions.

    The optimized prompt is scored with the baseline evaluation as the
    reference denominator on every split, matching how the final comparison is
    computed.  Already-cached split-level batch evaluations are reused; any
    missing evaluation is run and cached before the report is returned.
    """

    if evaluation_replicates < 1:
        raise ValueError("evaluation_replicates must be at least 1")
    baseline_digest_value = bundle_digest(baseline)
    optimized_digest_value = bundle_digest(optimized)
    splits: dict[str, Any] = {}
    for split, targets in targets_by_split.items():
        if not targets:
            continue
        baseline_batch = evaluate_bundle_repeated(
            runner,
            targets,
            baseline,
            candidate_dir,
            split=split,
            workspace_kind="baseline",
            replicates=evaluation_replicates,
        )
        optimized_kind = "baseline" if optimized_digest_value == baseline_digest_value else "candidate"
        optimized_batch = evaluate_bundle_repeated(
            runner,
            targets,
            optimized,
            candidate_dir,
            split=split,
            workspace_kind=optimized_kind,
            replicates=evaluation_replicates,
            reference_results=baseline_batch["results"],
        )
        splits[split] = {
            "baseline": _bundle_split_summary(baseline_batch),
            "optimized": _bundle_split_summary(optimized_batch),
            "environment_fingerprints": baseline_batch.get(
                "environment_fingerprints", {}
            ),
        }
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "baseline_digest": baseline_digest_value,
        "optimized_digest": optimized_digest_value,
        "evaluation_replicates": evaluation_replicates,
        "splits": splits,
    }


def _find_source_path(runner: CoverUpExperimentRunner, target: SymbolTarget) -> Path | None:
    source = Path(target.source_file)
    resolve_package = getattr(runner.config, "package_dir_for", None)
    if resolve_package is not None:
        package_dir = Path(resolve_package(target.project)).resolve()
    else:
        package_dir = Path(runner.config.package_dir).resolve()
    candidates = (
        package_dir.parent / source,
        package_dir / source,
        runner.config.project_root.resolve() / source,
        package_dir / source.name,
    )
    return next((path for path in candidates if path.is_file()), None)


def _definition_lines(source: str, symbol: str) -> set[int]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    wanted = symbol.split(".")
    matches: list[ast.AST] = []

    def visit(body: list[ast.stmt], scope: list[str]) -> None:
        for node in body:
            if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
                qualified = [*scope, node.name]
                if qualified == wanted or node.name == symbol:
                    matches.append(node)
                visit(node.body, qualified)
                continue
            # Nested definitions can live below control-flow nodes such as
            # if/try/match. Keep the lexical function/class scope while walking
            # those statement containers so qualified targets remain findable.
            children = [child for child in ast.iter_child_nodes(node) if isinstance(child, ast.stmt)]
            visit(children, scope)

    visit(tree.body, [])
    if not matches:
        return set()
    selected: set[int] = set()
    for node in matches:
        start = min([node.lineno, *(decorator.lineno for decorator in getattr(node, "decorator_list", []))])
        end = getattr(node, "end_lineno", node.lineno)
        selected.update(range(start, min(end, start + 14) + 1))
    return selected


def _source_context(
    runner: CoverUpExperimentRunner,
    target: SymbolTarget,
    coverage: dict | None,
    *,
    max_lines: int = 80,
) -> str:
    path = _find_source_path(runner, target)
    if path is None:
        return "Source file was not found in the configured project."
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    selected = _definition_lines(source, target.symbol)
    if coverage:
        focus = set(coverage.get("remaining_lines", []))
        for branch in coverage.get("remaining_branches", []):
            focus.update(line for line in branch if isinstance(line, int) and line > 0)
        for line in focus:
            selected.update(range(max(1, line - 2), min(len(lines), line + 2) + 1))
    ordered = sorted(line for line in selected if 1 <= line <= len(lines))[:max_lines]
    if not ordered:
        ordered = list(range(1, min(len(lines), max_lines) + 1))
    rendered = []
    previous = 0
    for line_number in ordered:
        if previous and line_number > previous + 1:
            rendered.append("...")
        rendered.append(f"{line_number:>5}: {lines[line_number - 1]}")
        previous = line_number
    return "\n".join(rendered)


_FAILURE_SEVERITY = {
    "model_request_failed": 1.0,
    "malformed_response": 1.0,
    "empty_response": 1.0,
    "missing_python_block": 1.0,
    "missing_imports": 0.9,
    "coverage_timeout": 0.9,
    "test_error_unrepairable": 1.0,
    "max_attempts_exhausted": 1.0,
    "test_error": 0.8,
    "no_coverage_gain_unrepairable": 0.9,
}


def _attempt_failure_severity(attempt: Mapping[str, Any]) -> float:
    outcome = str(attempt.get("outcome", ""))
    if outcome in _FAILURE_SEVERITY:
        return _FAILURE_SEVERITY[outcome]
    if outcome == "coverage_gain_saved":
        gained = len(attempt.get("gained_lines", [])) + len(attempt.get("gained_branches", []))
        remaining = len(attempt.get("remaining_lines", [])) + len(attempt.get("remaining_branches", []))
        total = gained + remaining
        return remaining / total if total else 0.0
    return 0.0


class CausalReflectionComponentSelector:
    """Select the prompt that produced the highest-impact observed failures."""

    def __call__(
        self,
        state: Any,
        trajectories: list[Mapping[str, Any]],
        subsample_scores: list[float],
        candidate_idx: int,
        candidate: dict[str, str],
    ) -> list[str]:
        del state, subsample_scores, candidate_idx
        priority = {component: 0.0 for component in candidate}
        evidence = {component: 0 for component in candidate}

        for trajectory in trajectories:
            if not _has_incomplete_coverage(trajectory):
                continue
            target_score = min(1.0, max(0.0, float(trajectory.get("score", 0.0))))
            target_gap = max(0.05, 1.0 - target_score)
            attempts = list(trajectory.get("attempt_traces", []))
            terminal_by_replicate: dict[int, int] = {}
            for index, attempt in enumerate(attempts):
                replicate = int(attempt.get("replicate", 0) or 0)
                terminal_by_replicate[replicate] = index

            for index, attempt in enumerate(attempts):
                component = str(attempt.get("component", ""))
                if component not in priority:
                    continue
                severity = _attempt_failure_severity(attempt)
                if severity <= 0:
                    continue
                replicate = int(attempt.get("replicate", 0) or 0)
                terminal_multiplier = 1.5 if terminal_by_replicate.get(replicate) == index else 1.0
                priority[component] += target_gap * severity * terminal_multiplier
                evidence[component] += 1

        eligible = [component for component in candidate if evidence.get(component, 0) > 0]
        if not eligible:
            # A no-op proposal is preferable to inventing a mutation without causal
            # evidence. GEPA will reject the duplicate candidate.
            return []

        selected = max(
            eligible,
            key=lambda component: (
                priority[component],
                evidence[component],
                component == "initial",
            ),
        )
        return [selected]


class LLMReflectionComponentSelector:
    """Let the reflection LM choose either component or both after any failure."""

    def __call__(
        self,
        state: Any,
        trajectories: list[Mapping[str, Any]],
        subsample_scores: list[float],
        candidate_idx: int,
        candidate: dict[str, str],
    ) -> list[str]:
        del state, subsample_scores, candidate_idx
        has_failure = any(
            _has_incomplete_coverage(trajectory)
            and str(attempt.get("component", "")) in candidate
            and _attempt_failure_severity(attempt) > 0
            for trajectory in trajectories
            for attempt in trajectory.get("attempt_traces", [])
        )
        return list(candidate) if has_failure else []


@dataclass
class PromptOptimizationResult:
    best_bundle: PromptBundle
    best_index: int
    candidates: list[PromptBundle]
    validation_scores: list[float]
    total_metric_calls: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "best_index": self.best_index,
            "best_candidate": self.best_bundle.as_candidate(),
            "validation_scores": self.validation_scores,
            "total_metric_calls": self.total_metric_calls,
            "candidates": [candidate.as_candidate() for candidate in self.candidates],
        }


class CoverUpPromptAdapter:
    """GEPA adapter whose candidate components are the actual CoverUp templates."""

    def __init__(
        self,
        *,
        runner: CoverUpExperimentRunner,
        candidate_dir: Path,
        targets_by_split: dict[str, list[SymbolTarget]],
        baseline: PromptBundle,
        reflection_lm: Any,
        evaluation_replicates: int = 1,
    ) -> None:
        self.runner = runner
        self.candidate_dir = candidate_dir
        self.targets_by_split = targets_by_split
        self.baseline = baseline
        self.baseline_digest = bundle_digest(baseline)
        self.reflection_lm = reflection_lm
        self.evaluation_replicates = evaluation_replicates
        self.reference_units: dict[tuple[str, str, str, str], tuple[int, int]] = {}
        self.max_component_chars = {
            name: max(MIN_COMPONENT_CHAR_BUDGET[name], len(text) * 3) for name, text in baseline.as_candidate().items()
        }
        self.candidate_lineage: dict[str, dict[str, Any]] = {}

    def _workspace_kind(self, bundle: PromptBundle) -> str:
        return "baseline" if bundle_digest(bundle) == self.baseline_digest else "candidate"

    def _remember_reference_units(self, results: list[dict]) -> None:
        for item in results:
            coverage = item.get("coverage")
            if coverage:
                self.reference_units[_result_identity(item)] = (
                    int(coverage["num_statements"]),
                    int(coverage["num_branches"]),
                )

    def _micro_coverage_components(
        self,
        result: dict,
        evaluated_results: list[dict],
        reference_targets: list[SymbolTarget],
    ) -> tuple[float, float, bool]:
        """Return per-target contributions whose mean is split micro coverage."""
        self._remember_reference_units(evaluated_results)
        reference_identities = [_target_identity(target) for target in reference_targets]
        # ``optimize`` preflights the baseline over the complete split, so the
        # denominator remains stable even when GEPA evaluates only a minibatch.
        # Direct adapter users without a preflight fall back to the evaluated
        # rows rather than assigning unknown targets zero executable units.
        identities = (
            reference_identities
            if reference_identities and all(identity in self.reference_units for identity in reference_identities)
            else [_result_identity(item) for item in evaluated_results]
        )
        total_statements = sum(self.reference_units.get(identity, (0, 0))[0] for identity in identities)
        total_branches = sum(self.reference_units.get(identity, (0, 0))[1] for identity in identities)
        coverage = result.get("coverage")
        valid = coverage is not None and coverage.get("valid") is not False
        covered_statements = int(coverage["covered_statements"]) if valid else 0
        covered_branches = int(coverage["covered_branches"]) if valid else 0
        count = len(identities)
        statement = count * covered_statements / total_statements if total_statements else 1.0
        branch = count * covered_branches / total_branches if total_branches else 1.0
        return statement, branch, bool(total_branches)

    def _weighted_score(
        self,
        result: dict,
        evaluated_results: list[dict],
        reference_targets: list[SymbolTarget],
    ) -> float:
        statement, branch, has_branches = self._micro_coverage_components(result, evaluated_results, reference_targets)
        if not has_branches:
            return statement
        return STATEMENT_SCORE_WEIGHT * statement + BRANCH_SCORE_WEIGHT * branch

    def _evaluate_replicates(
        self,
        targets: list[SymbolTarget],
        bundle: PromptBundle,
        *,
        split: str,
    ) -> list[dict]:
        return [
            evaluate_bundle_batch_cached(
                self.runner,
                targets,
                bundle,
                self.candidate_dir,
                split=split,
                workspace_kind=self._workspace_kind(bundle),
                replicate=replicate,
            )
            for replicate in range(self.evaluation_replicates)
        ]

    def _comparison_candidate(
        self,
        candidate: dict[str, str],
    ) -> tuple[dict[str, str], list[str], str]:
        digest = bundle_digest(PromptBundle.from_candidate(candidate))
        lineage = self.candidate_lineage.get(digest)
        if lineage is not None:
            return (
                dict(lineage["parent_candidate"]),
                list(lineage["changed_components"]),
                "parent",
            )
        baseline_candidate = self.baseline.as_candidate()
        changed = [
            component
            for component in COMPONENT_PLACEHOLDERS
            if candidate.get(component) != baseline_candidate[component]
        ]
        return baseline_candidate, changed, "baseline"

    def evaluate(
        self,
        batch: list[SymbolTarget],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> gepa_core.EvaluationBatch:
        bundle = PromptBundle.from_candidate(candidate)
        if not batch:
            return gepa_core.EvaluationBatch(outputs=[], scores=[], trajectories=[])
        splits = {target.split for target in batch}
        if len(splits) != 1:
            raise ValueError(f"GEPA minibatch mixes dataset splits: {sorted(splits)}")
        split = next(iter(splits))
        reference_targets = self.targets_by_split[split]
        validation_error = validate_bundle(bundle)
        if validation_error:
            outputs = [{"target": target.__dict__, "score": 0.0} for target in batch]
            trajectories = None
            if capture_traces:
                trajectories = [
                    {
                        "target": target.__dict__,
                        "score": 0.0,
                        "feedback": validation_error,
                        "source_context": _source_context(self.runner, target, None),
                    }
                    for target in batch
                ]
            return gepa_core.EvaluationBatch(
                outputs=outputs,
                scores=[0.0] * len(batch),
                trajectories=trajectories,
            )

        # GEPA deliberately supplies a reflection/evaluation minibatch here.
        # Run only that batch; complete split evaluations are reserved for the
        # baseline preflight and final validation paths outside this adapter.
        repeated_batches = self._evaluate_replicates(batch, bundle, split=split)
        lookups = [{_result_identity(result): result for result in record["results"]} for record in repeated_batches]
        comparison_lookups = lookups
        baseline_lookups = lookups
        comparison_digest = bundle_digest(bundle)
        baseline_digest = self.baseline_digest
        changed_components: list[str] = []
        comparison_source = "baseline"
        if capture_traces:
            parent_candidate, changed_components, comparison_source = self._comparison_candidate(candidate)
            parent_bundle = PromptBundle.from_candidate(parent_candidate)
            comparison_digest = bundle_digest(parent_bundle)
            batches_by_digest = {bundle_digest(bundle): repeated_batches}

            def comparison_batches(comparison_bundle: PromptBundle) -> list[dict]:
                comparison_bundle_digest = bundle_digest(comparison_bundle)
                if comparison_bundle_digest not in batches_by_digest:
                    batches_by_digest[comparison_bundle_digest] = self._evaluate_replicates(
                        batch, comparison_bundle, split=split
                    )
                return batches_by_digest[comparison_bundle_digest]

            parent_batches = comparison_batches(parent_bundle)
            baseline_batches = comparison_batches(self.baseline)
            comparison_lookups = [
                {_result_identity(result): result for result in record["results"]} for record in parent_batches
            ]
            baseline_lookups = [
                {_result_identity(result): result for result in record["results"]} for record in baseline_batches
            ]
        outputs = []
        scores = []
        objectives = []
        trajectories = [] if capture_traces else None
        for target in batch:
            identity = _target_identity(target)
            samples = [lookup[identity] for lookup in lookups]
            micro_coverage_samples = [
                self._micro_coverage_components(sample, record["results"], reference_targets)
                for sample, record in zip(samples, repeated_batches, strict=True)
            ]
            weighted_scores = [
                (STATEMENT_SCORE_WEIGHT * statement + BRANCH_SCORE_WEIGHT * branch if has_branches else statement)
                for statement, branch, has_branches in micro_coverage_samples
            ]
            raw_scores = [float(sample["score"]) for sample in samples]
            score = _mean(weighted_scores)
            raw_score = _mean(raw_scores)
            output = {
                "target": target.__dict__,
                "weighted_score": score,
                "raw_symbol_score": raw_score,
                "replicate_scores": raw_scores,
            }
            outputs.append(output)
            scores.append(score)
            objectives.append(
                {
                    # GEPA macro-averages objective values over validation targets.
                    # These scaled contributions therefore aggregate back to the
                    # same micro coverage components used by the weighted score.
                    "statement_coverage": _mean([statement for statement, _, _ in micro_coverage_samples]),
                    "branch_coverage": _mean([branch for _, branch, _ in micro_coverage_samples]),
                }
            )
            if trajectories is not None:
                parent_samples = [lookup[identity] for lookup in comparison_lookups]
                baseline_samples = [lookup[identity] for lookup in baseline_lookups]
                representative_replicate = min(
                    range(len(samples)),
                    key=lambda index: float(samples[index]["score"]),
                )
                worst = samples[representative_replicate]
                attempt_traces = _attempts_with_replicates(samples)
                parent_attempt_traces = _attempts_with_replicates(parent_samples)
                parent_replicate_scores = [float(sample["score"]) for sample in parent_samples]
                baseline_replicate_scores = [float(sample["score"]) for sample in baseline_samples]
                parent_score = _mean(parent_replicate_scores)
                baseline_score = _mean(baseline_replicate_scores)
                score_delta = raw_score - parent_score
                trajectories.append(
                    {
                        "target": target.__dict__,
                        "score": raw_score,
                        "candidate_score": raw_score,
                        "parent_score": parent_score,
                        "baseline_score": baseline_score,
                        "score_delta": score_delta,
                        "baseline_score_delta": raw_score - baseline_score,
                        "comparison_outcome": _comparison_outcome(score_delta),
                        "comparison_source": comparison_source,
                        "candidate_digest": bundle_digest(bundle),
                        "parent_digest": comparison_digest,
                        "baseline_digest": baseline_digest,
                        "changed_components": changed_components,
                        "weighted_score": score,
                        "replicate_scores": raw_scores,
                        "parent_replicate_scores": parent_replicate_scores,
                        "baseline_replicate_scores": baseline_replicate_scores,
                        "representative_replicate": representative_replicate,
                        "candidate_test": _representative_test(
                            samples[representative_replicate].get("attempt_traces", [])
                        ),
                        "parent_test": _representative_test(
                            parent_samples[representative_replicate].get("attempt_traces", [])
                        ),
                        "feedback": "\n\n".join(
                            f"Replicate {replicate}:\n{sample['feedback']}" for replicate, sample in enumerate(samples)
                        ),
                        "coverage": worst.get("coverage"),
                        "attempt_traces": attempt_traces,
                        "parent_attempt_traces": parent_attempt_traces,
                        "source_context": _source_context(self.runner, target, worst.get("coverage")),
                    }
                )
        return gepa_core.EvaluationBatch(
            outputs=outputs,
            scores=scores,
            trajectories=trajectories,
            objective_scores=objectives,
        )

    def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: gepa_core.EvaluationBatch,
        components_to_update: list[str],
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
        trajectories = eval_batch.trajectories
        if trajectories is None:
            raise ValueError("GEPA reflection requires captured CoverUp trajectories")
        trajectories = [trajectory for trajectory in trajectories if _has_incomplete_coverage(trajectory)]
        result: dict[str, list[dict[str, Any]]] = {}
        for component in components_to_update:
            placeholders = COMPONENT_PLACEHOLDERS[component]
            has_structured_traces = any(trajectory.get("attempt_traces") for trajectory in trajectories)
            component_trajectories = [
                trajectory
                for trajectory in trajectories
                if any(attempt.get("component") == component for attempt in trajectory.get("attempt_traces", []))
            ]
            # Compatibility for custom runners that predate trace schema 7. Real
            # traced runs never borrow evidence from an unexercised component.
            if not has_structured_traces:
                component_trajectories = list(trajectories)
            component_trajectories = _order_contrastive_trajectories(component_trajectories)
            result[component] = [
                {
                    "Inputs": {
                        "component": component,
                        "component_role": COMPONENT_ROLES[component],
                        "required_literal_placeholders": list(placeholders),
                        "target": (f"{trajectory['target']['source_file']}::{trajectory['target']['symbol']}"),
                        "active_component": component,
                        "changed_components": trajectory.get("changed_components", []),
                        "source_context": _clip_text(trajectory["source_context"], 12_000),
                    },
                    "Generated Outputs": {
                        "symbol_score": trajectory["score"],
                        "candidate_score": trajectory.get("candidate_score", trajectory["score"]),
                        "parent_score": trajectory.get("parent_score", trajectory["score"]),
                        "baseline_score": trajectory.get("baseline_score", trajectory["score"]),
                        "score_delta": trajectory.get("score_delta", 0.0),
                        "baseline_score_delta": trajectory.get("baseline_score_delta", 0.0),
                        "comparison_outcome": trajectory.get("comparison_outcome", "tied"),
                        "comparison_source": trajectory.get("comparison_source", "baseline"),
                        "exemplar_type": _exemplar_type(trajectory),
                        "replicate_scores": trajectory.get("replicate_scores", []),
                        "parent_replicate_scores": trajectory.get("parent_replicate_scores", []),
                        "baseline_replicate_scores": trajectory.get("baseline_replicate_scores", []),
                        "representative_replicate": trajectory.get("representative_replicate", 0),
                        "candidate_component_chars": len(candidate[component]),
                        "candidate_test": trajectory.get(
                            "candidate_test",
                            _representative_test(trajectory.get("attempt_traces", [])),
                        ),
                        "parent_test": trajectory.get(
                            "parent_test",
                            _representative_test(trajectory.get("parent_attempt_traces", [])),
                        ),
                        "execution_episodes": _build_execution_episodes(trajectory.get("attempt_traces", [])),
                    },
                    "Feedback": (
                        "Contrastive result: candidate "
                        f"{trajectory.get('comparison_outcome', 'tied')} versus "
                        f"{trajectory.get('comparison_source', 'baseline')} "
                        f"(delta={float(trajectory.get('score_delta', 0.0)):+.4f}).\n"
                        f"{_clip_text(trajectory['feedback'], 6_000, keep_tail=True)}\n"
                        "Use the labelled initial-to-repair episodes and compare the "
                        "candidate with its direct parent when present. Preserve causal "
                        "behaviors associated with positive deltas and correct behaviors "
                        "associated with regressions or failures. Infer one reusable prompting "
                        "improvement from the contrast. "
                        "Do not embed project-specific names or line numbers in the template."
                    ),
                }
                for trajectory in component_trajectories
            ]
        trace_path = self.candidate_dir / "reflection_traces.jsonl"
        trace_payload = {
            "schema_version": 2,
            "candidate_digest": bundle_digest(PromptBundle.from_candidate(candidate)),
            "components_to_update": list(components_to_update),
            "records": result,
        }
        with _digest_lock(f"reflection-trace:{trace_path.resolve()}"):
            trace_path.parent.mkdir(parents=True, exist_ok=True)
            with trace_path.open("a", encoding="utf-8") as trace_file:
                trace_file.write(json.dumps(trace_payload, ensure_ascii=False, default=str) + "\n")
        return result

    @staticmethod
    def _member(value: Any, name: str) -> Any:
        return value.get(name) if isinstance(value, Mapping) else getattr(value, name, None)

    @classmethod
    def _extract_function_call(
        cls,
        response: Any,
        expected_name: str,
    ) -> dict[str, Any] | None:
        if isinstance(response, str | bytes) or not isinstance(response, Sequence):
            return None
        if len(response) != 1:
            return None
        tool_calls = cls._member(response[0], "tool_calls")
        if not isinstance(tool_calls, Sequence) or len(tool_calls) != 1:
            return None
        function = cls._member(tool_calls[0], "function")
        if function is None:
            return None
        if cls._member(function, "name") != expected_name:
            return None
        arguments = cls._member(function, "arguments")
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                return None
        if not isinstance(arguments, dict):
            return None
        return arguments

    @classmethod
    def _extract_test_experiment(cls, response: Any) -> dict[str, str] | None:
        arguments = cls._extract_function_call(response, "run_test_experiment")
        if arguments is None or set(arguments) != {
            "case_id",
            "test_module",
            "hypothesis",
        }:
            return None
        if not all(
            isinstance(arguments[name], str) and arguments[name].strip()
            for name in ("case_id", "test_module", "hypothesis")
        ):
            return None
        return arguments

    @classmethod
    def _extract_component_update(cls, response: Any) -> dict[str, Any] | None:
        arguments = cls._extract_function_call(response, "update_prompt_component")
        if arguments is None:
            return None
        required = {
            "component",
            "replacements",
            "diagnosis",
            "evidence",
            "successful_experiment_ids",
        }
        if not required.issubset(arguments):
            return None
        if not isinstance(arguments["replacements"], dict):
            return None
        if not isinstance(arguments["diagnosis"], str) or not arguments["diagnosis"].strip():
            return None
        if (
            not isinstance(arguments["evidence"], list)
            or not arguments["evidence"]
            or not all(isinstance(item, str) and item.strip() for item in arguments["evidence"])
        ):
            return None
        if (
            not isinstance(arguments["successful_experiment_ids"], list)
            or not arguments["successful_experiment_ids"]
            or not all(isinstance(item, str) and item.strip() for item in arguments["successful_experiment_ids"])
        ):
            return None
        return arguments

    def _optimizer_experiment_cases(
        self,
        evidence: Mapping[str, Sequence[Mapping[str, Any]]],
    ) -> tuple[list[dict[str, Any]], dict[str, SymbolTarget]]:
        targets = {
            f"{target.source_file}::{target.symbol}": target
            for split_targets in self.targets_by_split.values()
            for target in split_targets
        }
        cases: list[dict[str, Any]] = []
        case_targets: dict[str, SymbolTarget] = {}
        seen: set[tuple[str, str]] = set()
        for component, records in evidence.items():
            for record in records:
                inputs = record.get("Inputs", {})
                outputs = record.get("Generated Outputs", {})
                label = str(inputs.get("target", ""))
                target = targets.get(label)
                if target is None or (component, label) in seen:
                    continue
                baseline_score = float(outputs.get("candidate_score", outputs.get("symbol_score", 0.0)))
                if not _has_incomplete_coverage({"score": baseline_score}):
                    continue
                seen.add((component, label))
                case_id = "case-" + hashlib.sha256(f"{component}\0{label}".encode()).hexdigest()[:10]
                case_targets[case_id] = target
                cases.append(
                    {
                        "case_id": case_id,
                        "component": component,
                        "target": label,
                        "baseline_score": baseline_score,
                        "source_context": _clip_text(inputs.get("source_context", ""), 12_000),
                        "failed_test": _clip_text(outputs.get("candidate_test", ""), 12_000),
                        "execution_episodes": outputs.get("execution_episodes", []),
                        "feedback": _clip_text(record.get("Feedback", ""), 6_000, keep_tail=True),
                    }
                )
        return cases, case_targets

    def _record_optimizer_experiment(self, payload: Mapping[str, Any]) -> None:
        path = self.candidate_dir / "optimizer_test_experiments.jsonl"
        with _digest_lock(f"optimizer-experiments:{path.resolve()}"):
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as output:
                output.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")

    def _run_optimizer_test_experiments(
        self,
        candidate: dict[str, str],
        cases: list[dict[str, Any]],
        case_targets: Mapping[str, SymbolTarget],
    ) -> list[dict[str, Any]]:
        history: list[dict[str, Any]] = []
        visible_cases = cases[:REFLECTION_MINIBATCH_SIZE]
        for attempt in range(1, MAX_OPTIMIZER_TEST_EXPERIMENTS + 1):
            prompt = f"""
You are the diagnostic teacher for a reusable pytest-generation prompt. Do not rewrite the prompt yet. First prove a concrete strategy by repairing one failed case with an executable test.

Current prompt templates:
<templates>{json.dumps(candidate, indent=2, ensure_ascii=False)}</templates>

Runnable failed cases:
<cases>{json.dumps(visible_cases, indent=2, ensure_ascii=False)}</cases>

Previous diagnostic experiments:
<experiment_history>{json.dumps(history, indent=2, ensure_ascii=False)}</experiment_history>

Choose one case. Infer a concrete causal defect in the failed test, then call run_test_experiment with a complete pytest module implementing the correction. You may revise a failed experiment on the next turn. Do not give generic advice and do not update the production prompt in this call.
"""
            request = {
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Find an executable counterexample before distilling a "
                            "prompt lesson. Call run_test_experiment exactly once."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "tools": [RUN_TEST_EXPERIMENT_TOOL],
                "tool_choice": {
                    "type": "function",
                    "function": {"name": "run_test_experiment"},
                },
            }
            log_reflection_request(request)
            try:
                response = self.reflection_lm(**request)
                log_full_reflection_event(
                    "optimizer_test_model_response",
                    {"attempt": attempt, "response": response},
                )
                proposed = self._extract_test_experiment(response)
            except (TypeError, ValueError) as exc:
                log_full_reflection_event(
                    "optimizer_test_response_error",
                    {"attempt": attempt, "error": repr(exc)},
                )
                proposed = None
            if proposed is None or proposed["case_id"] not in case_targets:
                invalid = {
                    "attempt": attempt,
                    "success": False,
                    "validation_error": "Invalid run_test_experiment tool call.",
                }
                history.append(invalid)
                log_full_reflection_event("optimizer_test_invalid_tool_call", invalid)
                continue
            case = next(value for value in visible_cases if value["case_id"] == proposed["case_id"])
            experiment_id = (
                f"{bundle_digest(PromptBundle.from_candidate(candidate))}-"
                f"{proposed['case_id']}-a{attempt}-{datetime.now(UTC).strftime('%H%M%S%f')}"
            )
            try:
                result = self.runner.evaluate_optimizer_test(
                    case_targets[proposed["case_id"]],
                    proposed["test_module"],
                    experiment_id=experiment_id,
                )
            except (OSError, RuntimeError, ValueError) as exc:
                result = {
                    "experiment_id": experiment_id,
                    "pytest_passed": False,
                    "score": 0.0,
                    "validation_error": str(exc),
                    "stdout": "",
                }
            improved = (
                bool(result.get("pytest_passed"))
                and float(result.get("score", 0.0)) > float(case["baseline_score"]) + 1e-9
            )
            experiment = {
                "attempt": attempt,
                "case_id": proposed["case_id"],
                "target": case["target"],
                "baseline_score": case["baseline_score"],
                "hypothesis": proposed["hypothesis"],
                "test_module": proposed["test_module"],
                "success": improved,
                "result": result,
            }
            history.append(experiment)
            log_full_reflection_event("optimizer_test_execution", experiment)
            self._record_optimizer_experiment(
                {
                    "schema_version": 1,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "candidate_digest": bundle_digest(PromptBundle.from_candidate(candidate)),
                    **experiment,
                }
            )
            if improved:
                break
        return history

    def _log_reflection_decision(
        self,
        candidate: dict[str, str],
        components: Sequence[str],
        *,
        status: str,
        selection: str | None = None,
        changed_components: Sequence[str] = (),
        detail: str | None = None,
        experiment_ids: Sequence[str] = (),
        optimizer_calls: int = 0,
    ) -> None:
        payload = {
            "schema_version": 1,
            "timestamp": datetime.now(UTC).isoformat(),
            "candidate_digest": bundle_digest(PromptBundle.from_candidate(candidate)),
            "experiment_first": True,
            "optimizer_calls": optimizer_calls,
            "offered_components": list(components),
            "selection": selection,
            "changed_components": list(changed_components),
            "status": status,
            "detail": detail,
            "successful_experiment_ids": list(experiment_ids),
        }
        path = self.candidate_dir / "reflection_decisions.jsonl"
        with _digest_lock(f"reflection-decisions:{path.resolve()}"):
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as output:
                output.write(json.dumps(payload, ensure_ascii=False) + "\n")
        log_full_reflection_event("reflection_decision", payload)
        changed = ",".join(changed_components) or "none"
        print(f"Reflection function call: status={status} selection={selection or 'none'} changed={changed}")

    def propose_new_texts(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        proposals = {component: candidate[component] for component in components_to_update}
        evidence = {component: list(reflective_dataset.get(component, [])) for component in components_to_update}
        if not any(evidence.values()):
            self._log_reflection_decision(candidate, components_to_update, status="no_failure_evidence")
            return proposals

        contracts = {
            component: {
                "role": COMPONENT_ROLES[component],
                "required_literal_placeholders": list(COMPONENT_PLACEHOLDERS[component]),
                "maximum_characters": self.max_component_chars[component],
            }
            for component in evidence
        }
        cases, case_targets = self._optimizer_experiment_cases(evidence)
        log_full_reflection_event(
            "optimizer_experiment_cases",
            {
                "candidate": candidate,
                "components_to_update": components_to_update,
                "cases": cases,
            },
        )
        if not cases:
            self._log_reflection_decision(
                candidate,
                components_to_update,
                status="no_runnable_experiment_case",
            )
            return proposals
        experiments = self._run_optimizer_test_experiments(candidate, cases, case_targets)
        successful = [item for item in experiments if item.get("success")]
        if not successful:
            self._log_reflection_decision(
                candidate,
                components_to_update,
                status="no_successful_test_experiment",
                optimizer_calls=len(experiments),
            )
            return proposals
        successful_ids = {str(item["result"]["experiment_id"]) for item in successful}
        prompt = f"""
You are optimizing a reusable two-stage CoverUp pytest-generation system. The stages are `initial` test generation and conditional `error` repair.

Current templates:
<templates>{json.dumps(candidate, indent=2, ensure_ascii=False)}</templates>

Eligible component contracts:
<contracts>{json.dumps(contracts, indent=2, ensure_ascii=False)}</contracts>

Labelled end-to-end execution evidence by component:
<evidence>{json.dumps(evidence, indent=2, ensure_ascii=False)}</evidence>

Optimizer-authored test experiments:
<test_experiments>{json.dumps(experiments, indent=2, ensure_ascii=False)}</test_experiments>

In one decision, choose `initial`, `error`, or `all`, then call `update_prompt_component` exactly once with every complete revised template selected. `all` is always allowed, even when direct evidence exists for only one stage. When selecting `all`, provide both `initial` and `error` replacements and change both; the update is rejected atomically otherwise. For a single component, provide only that component's replacement.

The successful diagnostic test is teacher evidence, not part of the candidate and not part of GEPA's score. Compare it with the failed generated test, identify the reusable causal lesson that made the experiment pass and cover more of the target, and turn that lesson into a detailed operational procedure suitable for a less-capable test-generation model. Do not compress away necessary intermediate checks merely to make the prompt short, and do not pad it with unrelated advice.

Use one strategy consistently: Reflexion. The revised templates must explicitly tell the test model how to:
1. OBSERVE the target source, requested missing lines/branches, dependencies, and (for `error`) the latest execution feedback.
2. REFLECT by naming the concrete branch preconditions or failed assumption and deciding what evidence is still missing; call `get_info` for that evidence rather than guessing APIs.
3. PLAN exact inputs, state setup, mocks/monkeypatch boundaries, invocation, and meaningful postconditions for each intended path.
4. ACT by writing a complete deterministic pytest module, then CHECK imports, reachability, assertions, cleanup, and preservation of already-valid behavior before answering.

Every instruction learned from evidence must have a concrete trigger, action, and verification criterion. Avoid unsupported generic advice such as "analyze carefully", "be robust", "handle edge cases", or "use appropriate mocks". Spell out the decision procedure; assume the downstream model will not infer omitted steps.

The template must also define an output protocol that CoverUp can parse safely: an optional concise reflection summary goes only inside `<REFLECTION>...</REFLECTION>` and contains no Python test code; the complete executable test module goes in exactly one fenced `python` block. No Python outside that block and no second `python` block. This reflection is a concise plan/root-cause summary, not a request to reveal private token-by-token chain-of-thought. The `error` replacement must apply the same protocol while explicitly comparing the failing behavior with the proposed repair.

Preserve useful instructions and required literal placeholders. Do not copy target-specific file names, symbols, line numbers, repository facts, assertions, constructor arguments, or literal values from the diagnostic test. Keep every replacement within its component's maximum length. Cite only successful experiment ids in successful_experiment_ids and explain the observed failed-to-successful behavior change in diagnosis and evidence. Do not answer with JSON or prose outside the function call.
"""
        messages = [
            {
                "role": "system",
                "content": (
                    "You optimize reusable CoverUp prompt components for a less-capable "
                    "test model. Distill execution-proven behavior into a detailed "
                    "Reflexion procedure with a strict reflection-versus-Python output "
                    "contract, then call update_prompt_component once."
                ),
            },
            {"role": "user", "content": prompt},
        ]
        tools = [UPDATE_PROMPT_COMPONENT_TOOL]
        tool_choice = {
            "type": "function",
            "function": {"name": "update_prompt_component"},
        }
        request = {
            "messages": messages,
            "tools": tools,
            "tool_choice": tool_choice,
        }
        log_reflection_request(request)
        try:
            response = self.reflection_lm(**request)
            log_full_reflection_event("prompt_update_model_response", response)
            update = self._extract_component_update(response)
        except (TypeError, ValueError) as exc:
            log_full_reflection_event("prompt_update_response_error", {"error": repr(exc)})
            update = None
        if update is None:
            self._log_reflection_decision(
                candidate,
                components_to_update,
                status="invalid_function_call",
                optimizer_calls=len(experiments) + 1,
            )
            return proposals

        cited_experiments = set(update["successful_experiment_ids"])
        if not cited_experiments or not cited_experiments.issubset(successful_ids):
            self._log_reflection_decision(
                candidate,
                components_to_update,
                status="unverified_experiment_evidence",
                experiment_ids=sorted(cited_experiments),
                optimizer_calls=len(experiments) + 1,
            )
            return proposals

        selection = str(update["component"])
        selected = set(evidence) if selection == "all" else {selection}
        if not selected or not selected.issubset(evidence):
            self._log_reflection_decision(
                candidate,
                components_to_update,
                status="invalid_selection",
                selection=selection,
            )
            return proposals
        if selection == "all" and selected != set(COMPONENT_PLACEHOLDERS):
            self._log_reflection_decision(
                candidate,
                components_to_update,
                status="invalid_all_contract",
                selection=selection,
            )
            return proposals
        replacements = update["replacements"]
        if set(replacements) != selected:
            self._log_reflection_decision(
                candidate,
                components_to_update,
                status="incomplete_replacements",
                selection=selection,
            )
            return proposals
        for component in selected:
            replacement = replacements[component]
            if not isinstance(replacement, str):
                self._log_reflection_decision(
                    candidate,
                    components_to_update,
                    status="invalid_replacement_type",
                    selection=selection,
                    detail=component,
                )
                return proposals
            if error := validate_template(replacement, COMPONENT_PLACEHOLDERS[component]):
                self._log_reflection_decision(
                    candidate,
                    components_to_update,
                    status="invalid_template",
                    selection=selection,
                    detail=f"{component}: {error}",
                )
                return proposals
            leaked_targets = [
                item["target"] for item in successful if str(item["target"]).lower() in replacement.lower()
            ]
            if leaked_targets:
                self._log_reflection_decision(
                    candidate,
                    components_to_update,
                    status="target_specific_replacement",
                    selection=selection,
                    detail=", ".join(leaked_targets),
                    experiment_ids=sorted(cited_experiments),
                    optimizer_calls=len(experiments) + 1,
                )
                return proposals
            if len(replacement) > self.max_component_chars[component]:
                self._log_reflection_decision(
                    candidate,
                    components_to_update,
                    status="template_too_long",
                    selection=selection,
                    detail=component,
                )
                return proposals
        if selection == "all" and any(replacements[component] == candidate[component] for component in selected):
            self._log_reflection_decision(
                candidate,
                components_to_update,
                status="all_requires_both_changes",
                selection=selection,
            )
            return proposals
        proposals.update(replacements)
        proposed_candidate = {**candidate, **proposals}
        changed_components = [
            component for component in components_to_update if proposed_candidate[component] != candidate[component]
        ]
        if changed_components:
            self.candidate_lineage[bundle_digest(PromptBundle.from_candidate(proposed_candidate))] = {
                "parent_candidate": dict(candidate),
                "changed_components": changed_components,
                "successful_experiment_ids": sorted(cited_experiments),
                "diagnosis": update["diagnosis"],
            }
            lesson_path = self.candidate_dir / "experiment_lessons.jsonl"
            lesson_payload = {
                "schema_version": 1,
                "timestamp": datetime.now(UTC).isoformat(),
                "parent_digest": bundle_digest(PromptBundle.from_candidate(candidate)),
                "candidate_digest": bundle_digest(PromptBundle.from_candidate(proposed_candidate)),
                "changed_components": changed_components,
                "successful_experiment_ids": sorted(cited_experiments),
                "diagnosis": update["diagnosis"],
                "evidence": update["evidence"],
            }
            log_full_reflection_event(
                "accepted_prompt_update",
                {
                    **lesson_payload,
                    "parent_candidate": candidate,
                    "proposed_candidate": proposed_candidate,
                    "model_update": update,
                },
            )
            with _digest_lock(f"experiment-lessons:{lesson_path.resolve()}"):
                lesson_path.parent.mkdir(parents=True, exist_ok=True)
                with lesson_path.open("a", encoding="utf-8") as output:
                    output.write(json.dumps(lesson_payload, ensure_ascii=False) + "\n")
        self._log_reflection_decision(
            candidate,
            components_to_update,
            status="accepted",
            selection=selection,
            changed_components=changed_components,
            experiment_ids=sorted(cited_experiments),
            optimizer_calls=len(experiments) + 1,
        )
        return proposals


def _optimization_run_digest(
    runner: CoverUpExperimentRunner,
    baseline: PromptBundle,
    train_targets: list[SymbolTarget],
    validation_targets: list[SymbolTarget],
    evaluation_replicates: int,
) -> str:
    payload = {
        "optimizer_schema": 15,
        "baseline": baseline.as_candidate(),
        "train": [_target_identity(target) for target in train_targets],
        "validation": [_target_identity(target) for target in validation_targets],
        "evaluation_replicates": evaluation_replicates,
        "train_evaluation": _evaluation_digest(runner, train_targets),
        "validation_evaluation": _evaluation_digest(runner, validation_targets),
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:12]


def validate_reference_evaluation(
    results: list[dict],
    *,
    split: str = "validation",
    expected_targets: Sequence[SymbolTarget] | None = None,
) -> None:
    """Reject a reference batch that cannot provide denominators for every target."""
    unusable = []
    actual_identities = set()
    for result in results:
        try:
            actual_identities.add(_result_identity(result))
        except (KeyError, TypeError):
            unusable.append("malformed target identity: result cannot be matched")
            continue
        coverage = result.get("coverage")
        denominator_valid = False
        if coverage is not None and coverage.get("valid") is not False:
            try:
                denominator_valid = int(coverage["num_statements"]) > 0 and int(coverage["num_branches"]) >= 0
            except (KeyError, TypeError, ValueError):
                denominator_valid = False
        if not denominator_valid:
            target = result.get("target", {})
            label = f"{target.get('source_file', '?')}::{target.get('symbol', '?')}"
            feedback_lines = [
                line.strip()
                for line in str(result.get("feedback", "No coverage data")).splitlines()
                if line.strip() and not re.fullmatch(r"Replicate \d+:?", line.strip())
            ]
            feedback = feedback_lines[0] if feedback_lines else "No coverage data"
            unusable.append(f"{label}: {feedback}")
    if expected_targets is not None:
        expected_identities = {_target_identity(target) for target in expected_targets}
        for identity in sorted(expected_identities - actual_identities):
            unusable.append(f"{identity[1]}::{identity[2]}: result is missing")
        for identity in sorted(actual_identities - expected_identities):
            unusable.append(f"{identity[1]}::{identity[2]}: unexpected result")
    if unusable:
        details = "\n".join(f"- {item}" for item in unusable[:10])
        raise RuntimeError(
            f"Baseline preflight cannot measure every {split} target. GEPA was "
            "stopped before spending its search budget because partial denominators "
            "would corrupt candidate scores. Fix or replace these targets, then use "
            f"a fresh artifacts directory:\n{details}"
        )


def optimize(
    *,
    runner: CoverUpExperimentRunner,
    train_targets: list[SymbolTarget],
    validation_targets: list[SymbolTarget],
    baseline: PromptBundle,
    reflection_lm: Any,
    artifacts_dir: Path,
    auto: str | None = "medium",
    max_metric_calls: int | None = None,
    evaluation_replicates: int = 1,
) -> PromptOptimizationResult:
    """Optimize the initial and error prompt components."""
    if error := validate_bundle(baseline):
        raise ValueError(f"Invalid baseline prompt bundle: {error}")
    if not train_targets or not validation_targets:
        raise ValueError("GEPA requires at least one train and one validation target")
    if evaluation_replicates < 1:
        raise ValueError("evaluation_replicates must be at least 1")
    if auto is not None:
        max_metric_calls = AUTO_METRIC_BUDGETS[auto]
    if max_metric_calls is None or max_metric_calls < 1:
        raise ValueError("A positive GEPA metric budget is required")

    adapter = CoverUpPromptAdapter(
        runner=runner,
        candidate_dir=artifacts_dir / "candidates",
        targets_by_split={"train": train_targets, "validation": validation_targets},
        baseline=baseline,
        reflection_lm=reflection_lm,
        evaluation_replicates=evaluation_replicates,
    )
    validation_baseline_aggregate: dict[str, Any] | None = None
    reflection_train_targets = list(train_targets)
    for preflight_split, preflight_targets in (
        ("train", train_targets),
        ("validation", validation_targets),
    ):
        baseline_preflight = evaluate_bundle_repeated(
            runner,
            preflight_targets,
            baseline,
            artifacts_dir / "candidates",
            split=preflight_split,
            workspace_kind="baseline",
            replicates=evaluation_replicates,
        )
        validate_reference_evaluation(
            baseline_preflight["results"],
            split=preflight_split,
            expected_targets=preflight_targets,
        )
        adapter._remember_reference_units(baseline_preflight["results"])
        if preflight_split == "train":
            incomplete = {
                _result_identity(result) for result in baseline_preflight["results"] if _has_incomplete_coverage(result)
            }
            reflection_train_targets = [target for target in train_targets if _target_identity(target) in incomplete]
        if preflight_split == "validation":
            validation_baseline_aggregate = baseline_preflight.get("aggregate") or (
                aggregate_coverage_score(baseline_preflight["results"])
            )
    assert validation_baseline_aggregate is not None
    baseline_metrics = {
        "score": float(validation_baseline_aggregate.get("score", 0.0)),
        "statement": float(validation_baseline_aggregate.get("statement_coverage", 0.0)),
        "branch": float(validation_baseline_aggregate.get("branch_coverage", 0.0)),
    }
    print(
        f"Iteration 0: Baseline validation aggregate metrics: {baseline_metrics}",
        flush=True,
    )
    print(
        f"Reflection train targets below 100% coverage: {len(reflection_train_targets)}/{len(train_targets)}",
        flush=True,
    )
    adapter.targets_by_split["train"] = reflection_train_targets
    if not reflection_train_targets:
        return PromptOptimizationResult(
            best_bundle=baseline,
            best_index=0,
            candidates=[baseline],
            validation_scores=[baseline_metrics["score"]],
            total_metric_calls=0,
        )
    run_digest = _optimization_run_digest(runner, baseline, train_targets, validation_targets, evaluation_replicates)
    result = gepa_core.optimize(
        seed_candidate=baseline.as_candidate(),
        trainset=reflection_train_targets,
        valset=validation_targets,
        adapter=adapter,
        reflection_lm=None,
        candidate_selection_strategy=BestParetoCandidateSelector(
            best_probability=0.7,
            rng=random.Random(7),
        ),
        frontier_type="hybrid",
        skip_perfect_score=False,
        reflection_minibatch_size=min(REFLECTION_MINIBATCH_SIZE, len(reflection_train_targets)),
        module_selector=LLMReflectionComponentSelector(),
        use_merge=True,
        max_merge_invocations=5,
        max_metric_calls=max_metric_calls,
        run_dir=str(artifacts_dir / "gepa_direct_logs" / run_digest),
        # The adapter already caches split/batch evaluations. GEPA's
        # per-example cache uses integer ids shared by its train and validation
        # ListDataLoaders, which can otherwise reuse a train score as validation.
        cache_evaluation=False,
        track_best_outputs=True,
        display_progress_bar=True,
        seed=7,
    )
    best_bundle = PromptBundle.from_candidate(result.best_candidate)
    if error := validate_bundle(best_bundle):
        raise ValueError(f"GEPA selected an invalid prompt bundle: {error}")
    return PromptOptimizationResult(
        best_bundle=best_bundle,
        best_index=result.best_idx,
        candidates=[PromptBundle.from_candidate(value) for value in result.candidates],
        validation_scores=[float(value) for value in result.val_aggregate_scores],
        total_metric_calls=int(result.total_metric_calls or 0),
    )
