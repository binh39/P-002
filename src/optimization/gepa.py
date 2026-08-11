from __future__ import annotations

import ast
import hashlib
import json
import re
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import gepa as gepa_core

from .metrics import aggregate_coverage_score
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
    "initial": "Generate the first complete pytest module from source and missing coverage.",
    "error": "Repair a complete pytest module after an execution or collection error.",
}
AUTO_METRIC_BUDGETS = {"light": 120, "medium": 300, "heavy": 600}

_DIGEST_LOCKS: dict[str, threading.Lock] = {}
_DIGEST_LOCKS_GUARD = threading.Lock()


def _digest_lock(key: str) -> threading.Lock:
    """Return the process-local lock that serializes one cached evaluation."""
    with _DIGEST_LOCKS_GUARD:
        return _DIGEST_LOCKS.setdefault(key, threading.Lock())


def validate_template(
    template: str, required_placeholders: tuple[str, ...] = INITIAL_PLACEHOLDERS,
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
    serialized = "\n---PROMPT---\n".join(
        (bundle.initial, bundle.error or "")
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def _cache_name(workspace_kind: str, replicate: int) -> str:
    stem = "baseline_batch" if workspace_kind == "baseline" else "batch"
    return f"{stem}.json" if replicate == 0 else f"{stem}_r{replicate}.json"


def _evaluation_digest(
    runner: CoverUpExperimentRunner, targets: list[SymbolTarget],
) -> str:
    """Fingerprint every input that can change a cached prompt evaluation."""
    config = getattr(runner, "config", None)
    config_values = {
        name: str(getattr(config, name, ""))
        for name in (
            "coverup_model", "max_attempts", "repeat_tests", "pytest_args",
            "max_concurrency", "rate_limit",
        )
    }
    source_hashes = {}
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
                project_root / source,
                package_dir / source.name,
            )
            path = next((value for value in candidates if value.is_file()), None)
            if path is not None:
                source_hashes[target.source_file] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
    payload = {
        # Schema 10 fixed PYTHONHASHSEED across CoverUp and coverage subprocesses.
        # Schema 11 makes repeat_tests effective during generation and final
        # scoring. Schema 12 preserves denominators from pytest exit 1 while
        # assigning failing generated suites zero covered units. Schema 13
        # batches CoverUp generation and scores only each target's traced tests.
        # Schema 14 restores isolated per-target CoverUp processes in one bounded
        # pool, consolidates traced tests, and skips redundant final-suite coverage.
        "cache_schema": 14,
        "config": config_values,
        "targets": [_target_identity(target) for target in targets],
        "sources": source_hashes,
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
    raise KeyError(
        f"Target {wanted!r} is absent from cached batch {batch.get('run_ids', [])}"
    )


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
        raise ValueError(
            f"Batch targets do not match requested split {split!r}: {sorted(target_splits)}"
        )

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
    lock_key = (
        f"{digest}:{evaluation_digest}:{split}:{workspace_kind}:{replicate}"
    )
    with _digest_lock(lock_key):
        candidate_dir.mkdir(parents=True, exist_ok=True)
        candidate = candidate_dir / f"{digest}.json"
        if not candidate.exists():
            bundle.save(candidate)

        safe_split = re.sub(r"[^A-Za-z0-9_.-]+", "_", split).strip("._-")
        if not safe_split:
            raise ValueError("split must contain at least one safe path character")
        cache_path = (
            candidate_dir / "evaluations" / digest / evaluation_digest / safe_split
            / _cache_name(workspace_kind, replicate)
        )
        if cache_path.exists():
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            requested = {_target_identity(target) for target in targets}
            cached_targets = {
                _result_identity(result) for result in cached.get("results", [])
            }
            if cached_targets != requested:
                raise RuntimeError(
                    f"Cached batch target set differs for candidate {digest} split {split!r}. "
                    "Use a fresh artifacts directory."
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
        records = [runner.evaluate_batch(
            targets,
            candidate,
            candidate_id=run_candidate_id,
            split=split,
            workspace_kind=workspace_kind,
        )]

        results = []
        for record in records:
            if len(record.results) != len(targets):
                raise RuntimeError(
                    "Minibatch evaluation returned an unexpected result count: "
                    f"{len(record.results)} for {len(targets)} targets"
                )
            for target_result in record.results:
                target = target_result.target
                results.append({
                    "prompt_digest": digest,
                    "evaluation_digest": evaluation_digest,
                    "replicate": replicate,
                    "target": target.__dict__,
                    "run_id": record.run_id,
                    "score": (
                        float(target_result.score["score"])
                        if target_result.score else 0.0
                    ),
                    "coverage": target_result.score,
                    "feedback": target_result.feedback,
                    "attempt_traces": getattr(target_result, "attempt_traces", []),
                })
        batch = {
            "prompt_digest": digest,
            "evaluation_digest": evaluation_digest,
            "replicate": replicate,
            "split": split,
            "workspace_kind": workspace_kind,
            "run_ids": [record.run_id for record in records],
            "generator_exit_codes": [
                int(getattr(record, "exit_code", 0) or 0) for record in records
            ],
            "tests_workspaces": [record.tests_workspace for record in records],
            "results": results,
        }
        batch["aggregate"] = aggregate_coverage_score(results)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(batch, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return batch


def _target_identity(target: SymbolTarget) -> tuple[str, str, str, str]:
    return target.project, target.source_file, target.symbol, target.split


def _result_identity(result: dict) -> tuple[str, str, str, str]:
    target = result["target"]
    return (
        target["project"], target["source_file"], target["symbol"], target["split"]
    )


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _clip_text(value: Any, limit: int, *, keep_tail: bool = False) -> str:
    text = str(value or "")
    if len(text) <= limit:
        return text
    marker = f"\n... [truncated {len(text) - limit} characters] ...\n"
    available = max(0, limit - len(marker))
    return marker + text[-available:] if keep_tail else text[:available] + marker


def _compact_component_attempts(
    attempts: Sequence[Mapping[str, Any]], component: str,
) -> list[dict[str, Any]]:
    """Keep concise causal evidence instead of sending entire pytest transcripts."""
    matching = [attempt for attempt in attempts if attempt.get("component") == component]
    compact = []
    for attempt in matching[-2:]:
        row = {
            key: attempt[key]
            for key in (
                "attempt", "replicate", "component", "outcome", "next_component",
                "finish_reason", "missing_imports", "gained_lines", "gained_branches",
                "remaining_lines", "remaining_branches",
            )
            if key in attempt
        }
        if "prompt_input" in attempt:
            row["prompt_input"] = _clip_text(
                attempt["prompt_input"], 8_000, keep_tail=True
            )
        if "generated_test" in attempt:
            row["generated_test"] = _clip_text(attempt["generated_test"], 12_000)
        if "execution_error" in attempt:
            row["execution_error"] = _clip_text(
                attempt["execution_error"], 8_000, keep_tail=True
            )
        if "assistant_response" in attempt:
            row["assistant_response"] = _clip_text(
                attempt["assistant_response"], 4_000
            )
        compact.append(row)
    return compact


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
    negative = [
        trajectory for trajectory in values
        if _exemplar_type(trajectory) in {"regression", "failure"}
    ]
    positive = [
        trajectory for trajectory in values
        if _exemplar_type(trajectory) == "positive"
    ]
    representatives: list[Mapping[str, Any]] = []
    if negative:
        representatives.append(min(
            negative,
            key=lambda trajectory: (
                float(trajectory.get("score_delta", 0.0)),
                float(trajectory.get("score", 0.0)),
            ),
        ))
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
        *(
            trajectory for trajectory in values
            if all(trajectory is not value for value in representatives)
        ),
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
        aggregate_coverage_score(
            batch["results"], reference_results=reference_results,
        )
        for batch in batches
    ]
    aggregate_keys = {
        key for row in aggregate_rows for key, value in row.items()
        if isinstance(value, (int, float))
    }
    aggregate = {
        key: _mean([float(row[key]) for row in aggregate_rows if key in row])
        for key in sorted(aggregate_keys)
    }
    merged_results = []
    for target in targets:
        identity = _target_identity(target)
        samples = [
            result for batch in batches for result in batch["results"]
            if _result_identity(result) == identity
        ]
        representative = dict(samples[0])
        representative["score"] = _mean([float(item["score"]) for item in samples])
        representative["replicate_scores"] = [float(item["score"]) for item in samples]
        coverages = [item.get("coverage") for item in samples if item.get("coverage")]
        if coverages:
            merged_coverage = dict(coverages[0])
            numeric_keys = (
                "score", "statement_gain", "branch_gain", "statement_coverage",
                "branch_coverage", "covered_statements", "num_statements",
                "covered_branches", "num_branches",
            )
            for key in numeric_keys:
                values = [
                    float(coverage[key]) for coverage in coverages if key in coverage
                ]
                if values:
                    merged_coverage[key] = _mean(values)
            merged_coverage["valid"] = all(
                coverage.get("valid") is not False for coverage in coverages
            )
            representative["coverage"] = merged_coverage
        representative["feedback"] = "\n\n".join(
            f"Replicate {index}:\n{item['feedback']}"
            for index, item in enumerate(samples)
        )
        merged_results.append(representative)
    return {
        "prompt_digest": bundle_digest(bundle),
        "split": split,
        "workspace_kind": workspace_kind,
        "replicates": replicates,
        "run_ids": [
            run_id for batch in batches for run_id in batch.get("run_ids", [])
        ],
        "tests_workspaces": [
            workspace
            for batch in batches
            for workspace in batch.get("tests_workspaces", [])
        ],
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
        optimized_kind = (
            "baseline" if optimized_digest_value == baseline_digest_value else "candidate"
        )
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
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                qualified = [*scope, node.name]
                if qualified == wanted or node.name == symbol:
                    matches.append(node)
                visit(node.body, qualified)

    visit(tree.body, [])
    if not matches:
        return set()
    node = matches[0]
    start = min(
        [node.lineno, *(decorator.lineno for decorator in getattr(node, "decorator_list", []))]
    )
    end = getattr(node, "end_lineno", node.lineno)
    return set(range(start, min(end, start + 14) + 1))


def _source_context(
    runner: CoverUpExperimentRunner, target: SymbolTarget, coverage: dict | None,
    *, max_lines: int = 80,
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
            name: max(600, len(text) * 3)
            for name, text in baseline.as_candidate().items()
        }
        self.candidate_lineage: dict[str, dict[str, Any]] = {}

    def _workspace_kind(self, bundle: PromptBundle) -> str:
        return "baseline" if bundle_digest(bundle) == self.baseline_digest else "candidate"

    def _remember_reference_units(self, results: list[dict]) -> None:
        for item in results:
            coverage = item.get("coverage")
            if coverage:
                self.reference_units[_result_identity(item)] = (
                    int(coverage["num_statements"]), int(coverage["num_branches"])
                )

    def _weighted_score(
        self,
        result: dict,
        evaluated_results: list[dict],
        reference_targets: list[SymbolTarget],
    ) -> float:
        self._remember_reference_units(evaluated_results)
        reference_identities = [
            _target_identity(target) for target in reference_targets
        ]
        # ``optimize`` preflights the baseline over the complete split, so the
        # denominator remains stable even when GEPA evaluates only a minibatch.
        # Direct adapter users without a preflight fall back to the evaluated
        # rows rather than assigning unknown targets zero executable units.
        identities = (
            reference_identities
            if reference_identities
            and all(identity in self.reference_units for identity in reference_identities)
            else [_result_identity(item) for item in evaluated_results]
        )
        total_statements = sum(
            self.reference_units.get(identity, (0, 0))[0] for identity in identities
        )
        total_branches = sum(
            self.reference_units.get(identity, (0, 0))[1] for identity in identities
        )
        coverage = result.get("coverage")
        valid = coverage is not None and coverage.get("valid") is not False
        covered_statements = int(coverage["covered_statements"]) if valid else 0
        covered_branches = int(coverage["covered_branches"]) if valid else 0
        count = len(identities)
        statement = (
            count * 0.4 * covered_statements / total_statements
            if total_statements else 0.4
        )
        branch = (
            count * 0.6 * covered_branches / total_branches
            if total_branches else 0.6
        )
        return statement + branch

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
        self, candidate: dict[str, str],
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
            component for component in COMPONENT_PLACEHOLDERS
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
        lookups = [
            {_result_identity(result): result for result in record["results"]}
            for record in repeated_batches
        ]
        comparison_lookups = lookups
        baseline_lookups = lookups
        comparison_digest = bundle_digest(bundle)
        baseline_digest = self.baseline_digest
        changed_components: list[str] = []
        comparison_source = "baseline"
        if capture_traces:
            parent_candidate, changed_components, comparison_source = (
                self._comparison_candidate(candidate)
            )
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
                {_result_identity(result): result for result in record["results"]}
                for record in parent_batches
            ]
            baseline_lookups = [
                {_result_identity(result): result for result in record["results"]}
                for record in baseline_batches
            ]
        outputs = []
        scores = []
        objectives = []
        trajectories = [] if capture_traces else None
        for target in batch:
            identity = _target_identity(target)
            samples = [lookup[identity] for lookup in lookups]
            weighted_scores = [
                self._weighted_score(
                    sample, record["results"], reference_targets
                )
                for sample, record in zip(samples, repeated_batches, strict=True)
            ]
            raw_scores = [float(sample["score"]) for sample in samples]
            coverage_samples = [sample.get("coverage") for sample in samples]
            valid_coverage = [coverage for coverage in coverage_samples if coverage]
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
            objectives.append({
                "statement": _mean([
                    float(coverage.get("statement_gain", 0.0))
                    for coverage in valid_coverage
                ]),
                "branch": _mean([
                    float(coverage.get("branch_gain", 0.0))
                    for coverage in valid_coverage
                ]),
            })
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
                baseline_attempt_traces = _attempts_with_replicates(baseline_samples)
                parent_replicate_scores = [
                    float(sample["score"]) for sample in parent_samples
                ]
                baseline_replicate_scores = [
                    float(sample["score"]) for sample in baseline_samples
                ]
                parent_score = _mean(parent_replicate_scores)
                baseline_score = _mean(baseline_replicate_scores)
                score_delta = raw_score - parent_score
                trajectories.append({
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
                        parent_samples[representative_replicate].get(
                            "attempt_traces", []
                        )
                    ),
                    "baseline_test": _representative_test(
                        baseline_samples[representative_replicate].get(
                            "attempt_traces", []
                        )
                    ),
                    "feedback": "\n\n".join(
                        f"Replicate {replicate}:\n{sample['feedback']}"
                        for replicate, sample in enumerate(samples)
                    ),
                    "coverage": worst.get("coverage"),
                    "attempt_traces": attempt_traces,
                    "parent_attempt_traces": parent_attempt_traces,
                    "baseline_attempt_traces": baseline_attempt_traces,
                    "source_context": _source_context(
                        self.runner, target, worst.get("coverage")
                    ),
                })
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
        result: dict[str, list[dict[str, Any]]] = {}
        for component in components_to_update:
            placeholders = COMPONENT_PLACEHOLDERS[component]
            has_structured_traces = any(
                trajectory.get("attempt_traces") for trajectory in trajectories
            )
            component_trajectories = [
                trajectory for trajectory in trajectories
                if any(
                    attempt.get("component") == component
                    for attempt in trajectory.get("attempt_traces", [])
                )
            ]
            # Compatibility for custom runners that predate trace schema 7. Real
            # traced runs never borrow evidence from an unexercised component.
            if not has_structured_traces:
                component_trajectories = list(trajectories)
            component_trajectories = _order_contrastive_trajectories(
                component_trajectories
            )
            result[component] = [
                {
                    "Inputs": {
                        "component": component,
                        "component_role": COMPONENT_ROLES[component],
                        "required_literal_placeholders": list(placeholders),
                        "target": (
                            f"{trajectory['target']['source_file']}::"
                            f"{trajectory['target']['symbol']}"
                        ),
                        "active_component": component,
                        "changed_components": trajectory.get(
                            "changed_components", []
                        ),
                        "source_context": _clip_text(
                            trajectory["source_context"], 12_000
                        ),
                    },
                    "Generated Outputs": {
                        "symbol_score": trajectory["score"],
                        "candidate_score": trajectory.get(
                            "candidate_score", trajectory["score"]
                        ),
                        "parent_score": trajectory.get(
                            "parent_score", trajectory["score"]
                        ),
                        "baseline_score": trajectory.get(
                            "baseline_score", trajectory["score"]
                        ),
                        "score_delta": trajectory.get("score_delta", 0.0),
                        "baseline_score_delta": trajectory.get(
                            "baseline_score_delta", 0.0
                        ),
                        "comparison_outcome": trajectory.get(
                            "comparison_outcome", "tied"
                        ),
                        "comparison_source": trajectory.get(
                            "comparison_source", "baseline"
                        ),
                        "exemplar_type": _exemplar_type(trajectory),
                        "replicate_scores": trajectory.get("replicate_scores", []),
                        "parent_replicate_scores": trajectory.get(
                            "parent_replicate_scores", []
                        ),
                        "baseline_replicate_scores": trajectory.get(
                            "baseline_replicate_scores", []
                        ),
                        "representative_replicate": trajectory.get(
                            "representative_replicate", 0
                        ),
                        "candidate_component_chars": len(candidate[component]),
                        "candidate_test": trajectory.get(
                            "candidate_test",
                            _representative_test(trajectory.get("attempt_traces", [])),
                        ),
                        "parent_test": trajectory.get(
                            "parent_test",
                            _representative_test(
                                trajectory.get("parent_attempt_traces", [])
                            ),
                        ),
                        "baseline_test": trajectory.get(
                            "baseline_test",
                            _representative_test(
                                trajectory.get("baseline_attempt_traces", [])
                            ),
                        ),
                        "component_attempts": _compact_component_attempts(
                            trajectory.get("attempt_traces", []), component
                        ),
                    },
                    "Feedback": (
                        "Contrastive result: candidate "
                        f"{trajectory.get('comparison_outcome', 'tied')} versus "
                        f"{trajectory.get('comparison_source', 'baseline')} "
                        f"(delta={float(trajectory.get('score_delta', 0.0)):+.4f}).\n"
                        f"{_clip_text(trajectory['feedback'], 6_000, keep_tail=True)}\n"
                        "Compare the candidate and parent/baseline tests. Preserve causal "
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
            "schema_version": 1,
            "candidate_digest": bundle_digest(PromptBundle.from_candidate(candidate)),
            "components_to_update": list(components_to_update),
            "records": result,
        }
        with _digest_lock(f"reflection-trace:{trace_path.resolve()}"):
            trace_path.parent.mkdir(parents=True, exist_ok=True)
            with trace_path.open("a", encoding="utf-8") as trace_file:
                trace_file.write(
                    json.dumps(trace_payload, ensure_ascii=False, default=str) + "\n"
                )
        return result

    @staticmethod
    def _lm_text(raw: Any) -> str:
        if isinstance(raw, str):
            return raw
        if isinstance(raw, Sequence) and raw:
            first = raw[0]
            if isinstance(first, str):
                return first
            if isinstance(first, dict) and "text" in first:
                return str(first["text"])
        raise TypeError("Reflection LM returned no usable text")

    @staticmethod
    def _extract_template(response: str) -> str:
        match = re.search(r"<template>\s*(.*?)\s*</template>", response, re.DOTALL)
        if match:
            return match.group(1).strip()
        stripped = response.strip()
        if stripped.startswith("```") and stripped.endswith("```"):
            stripped = re.sub(r"^```[^\n]*\n?", "", stripped)
            stripped = stripped[:-3]
        return stripped.strip()

    def propose_new_texts(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        proposals: dict[str, str] = {}
        for component in components_to_update:
            current = candidate[component]
            evidence_rows = list(reflective_dataset.get(component, []))
            if not evidence_rows:
                proposals[component] = current
                continue
            evidence = json.dumps(
                evidence_rows,
                indent=2,
                ensure_ascii=False,
            )
            placeholders = COMPONENT_PLACEHOLDERS[component]
            prompt = f"""
You are optimizing one reusable CoverUp pytest-generation template that will be used by another LLM to generate Python tests.
Your goal is to improve the template so that the downstream test-generation LLM produces higher-quality pytest tests with the highest achievable code coverage, with particular emphasis on:
1. Branch coverage
2. Statement coverage
The final optimization score is defined as: score = 0.4 * statement_coverage + 0.6 * branch_coverage.
Therefore, branch coverage is more important than statement coverage, but the optimized template should improve both whenever possible.
Component: {component} Role: {COMPONENT_ROLES[component]}
Required literal placeholders: {', '.join(placeholders)}
Maximum length: {self.max_component_chars[component]} characters
Current template: <current_template> {current} </current_template>
Contrastive execution evidence from representative successful, failing, and regressed targets: <evidence> {evidence} </evidence>
Your task is to revise the current template so that a downstream LLM is more likely to generate effective tests that exercise previously uncovered statements and branches.
Analyze the execution evidence carefully before making any change. When optimizing the template, follow these principles:
1. Optimize for coverage behavior, not wording quality alone. The revised template should cause the downstream LLM to make better testing decisions, not merely make the instruction sound clearer or more polished.
2. Prioritize branch coverage. Because branch coverage contributes 60% of the final score, prefer changes that help the downstream LLM: - identify uncovered decision outcomes, - reason about both true and false branches, - exercise alternative control-flow paths, - reach nested and compound conditions, - trigger exception-handling branches, - cover early returns, - cover loop-entry and loop-exit behavior, - cover match/case alternatives when applicable, - and construct inputs that force execution through currently uncovered branches.
3. Improve statement coverage as well. Encourage the downstream LLM to reach executable statements that remain uncovered, especially statements that are only reachable through specific branches, state configurations, exceptions, boundary values, or dependency behavior.
4. Learn from contrastive evidence. Compare successful, failing, and regressed targets and infer general patterns such as: - which testing strategies consistently increase coverage, - which instructions cause the test generator to miss important paths, - which behaviors lead to regressions, - which kinds of inputs expose additional branches, - which setup or mocking strategies help execution reach deeper code, - and which unnecessary behaviors waste test-generation effort.
5. Convert observed failures into reusable operational guidance. If evidence shows that the downstream LLM repeatedly misses a particular class of behavior, revise the template to explicitly guide it toward a better strategy.
Prefer rules such as:
- inspect uncovered control-flow before adding redundant tests,
- target uncovered branch outcomes directly,
- vary one relevant input or state dimension at a time,
- reason about preconditions required to reach a target branch,
- use boundary, empty, null-like, invalid, exceptional, and alternative-state inputs when relevant,
- minimize duplicated tests that execute already-covered paths,
- repair failing tests when those failures prevent execution from reaching useful code,
- and prioritize tests that are likely to unlock multiple uncovered statements or branches.
6. Encourage coverage-directed iteration. The optimized instruction should make the downstream LLM use available coverage feedback as a search signal:
- identify what remains uncovered,
- infer why it remains uncovered,
- propose a test specifically targeting it,
- execute or validate that test when the surrounding system allows it,
- and avoid spending effort on already-saturated paths.
7. Prefer actionable guidance over generic statements. Avoid vague instructions such as:
- "write comprehensive tests",
- "maximize coverage",
- "consider edge cases", unless they are accompanied by concrete operational guidance explaining how to do so.
8. Do not overfit to individual examples. Never include target-specific:
- file names,
- function names,
- class names,
- variable names,
- literal line numbers,
- repository-specific details,
- exact test values that only apply to one target,
- or implementation-specific facts that would not generalize.
9. Preserve useful existing behavior. The new template should be a conservative improvement over the current template.
Do not remove effective instructions unless the evidence clearly indicates that they are harmful, redundant, misleading, or consume valuable prompt space.
10. Prefer concise, high-value instructions. The template has a strict character limit. Each added instruction should justify its cost by being likely to improve downstream coverage behavior.
Remove redundancy, repeated goals, unnecessary explanations, scoring formulas, or generic testing advice if they do not directly help the downstream LLM generate better tests.
11. Respect the optimization objective. When there is a trade-off between two possible revisions, prefer the revision that is more likely to improve: 0.4 * statement_coverage + 0.6 * branch_coverage In particular, a revision that significantly improves branch exploration may be preferable even if its statement-coverage improvement is smaller.
12. Preserve all required placeholders exactly. Every required literal placeholder listed above must appear exactly as required in the revised template. Do not rename, remove, escape, paraphrase, or alter them. 13. Keep the revised template general and reusable. It must remain suitable for many different Python functions, modules, repositories, and testing situations. Before producing the final revision, internally determine:
- what behavior in the current template is already effective,
- what specific weakness is supported by the evidence,
- what single or small set of changes is most likely to improve downstream branch and statement coverage,
- and whether the change is sufficiently general to help unseen targets. Propose one conservative, evidence-supported revision of the template. Return only the complete revised template between the following tags: <template> ... </template>
Do not include explanations, analysis, markdown fences, scores, comments, or any text outside the <template> tags.
"""
            last_error = ""
            for _ in range(2):
                response = self._lm_text(self.reflection_lm(prompt))
                proposal = self._extract_template(response)
                error = validate_template(proposal, placeholders)
                if not error and len(proposal) <= self.max_component_chars[component]:
                    proposals[component] = proposal
                    break
                last_error = error or (
                    f"Template has {len(proposal)} characters, above the allowed "
                    f"{self.max_component_chars[component]}."
                )
                prompt += (
                    f"\nThe previous response was invalid: {last_error}\n"
                    "Return a corrected complete template and nothing else."
                )
            else:
                raise ValueError(
                    f"Reflection LM failed to produce a valid {component} template: "
                    f"{last_error}"
                )
        proposed_candidate = {**candidate, **proposals}
        changed_components = [
            component for component in components_to_update
            if proposed_candidate[component] != candidate[component]
        ]
        if changed_components:
            self.candidate_lineage[
                bundle_digest(PromptBundle.from_candidate(proposed_candidate))
            ] = {
                "parent_candidate": dict(candidate),
                "changed_components": changed_components,
            }
        return proposals


def _optimization_run_digest(
    runner: CoverUpExperimentRunner,
    baseline: PromptBundle,
    train_targets: list[SymbolTarget],
    validation_targets: list[SymbolTarget],
    evaluation_replicates: int,
) -> str:
    payload = {
        "optimizer_schema": 8,
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
    results: list[dict], *, split: str = "validation",
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
                denominator_valid = (
                    int(coverage["num_statements"]) > 0
                    and int(coverage["num_branches"]) >= 0
                )
            except (KeyError, TypeError, ValueError):
                denominator_valid = False
        if not denominator_valid:
            target = result.get("target", {})
            label = f"{target.get('source_file', '?')}::{target.get('symbol', '?')}"
            feedback_lines = [
                line.strip()
                for line in str(
                    result.get("feedback", "No coverage data")
                ).splitlines()
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
    run_digest = _optimization_run_digest(
        runner, baseline, train_targets, validation_targets, evaluation_replicates
    )
    result = gepa_core.optimize(
        seed_candidate=baseline.as_candidate(),
        trainset=train_targets,
        valset=validation_targets,
        adapter=adapter,
        reflection_lm=None,
        candidate_selection_strategy="pareto",
        frontier_type="hybrid",
        skip_perfect_score=False,
        reflection_minibatch_size=min(8, len(train_targets)),
        module_selector="round_robin",
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
