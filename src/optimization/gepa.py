from __future__ import annotations

import ast
import hashlib
import json
import re
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import gepa as gepa_core

from .metrics import aggregate_coverage_score
from .models import SymbolTarget
from .prompts import PromptBundle
from .runner import CoverUpExperimentRunner

INITIAL_PLACEHOLDERS = ("{filename}", "{missing_coverage}", "{source_excerpt}")
ERROR_PLACEHOLDERS = ("{error}",)
MISSING_COVERAGE_PLACEHOLDERS = ("{missing_coverage}",)
COMPONENT_PLACEHOLDERS = {
    "initial": INITIAL_PLACEHOLDERS,
    "error": ERROR_PLACEHOLDERS,
    "missing_coverage": MISSING_COVERAGE_PLACEHOLDERS,
}
COMPONENT_ROLES = {
    "initial": "Generate the first complete pytest module from source and missing coverage.",
    "error": "Repair a complete pytest module after an execution or collection error.",
    "missing_coverage": "Revise a passing test module to cover the remaining lines and branches.",
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
            missing_coverage="line 1",
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
        (
            "missing_coverage",
            bundle.missing_coverage or "",
            MISSING_COVERAGE_PLACEHOLDERS,
        ),
    )
    for name, template, placeholders in templates:
        if error := validate_template(template, placeholders):
            return f"Invalid {name} prompt: {error}"
    return None


def bundle_digest(bundle: PromptBundle) -> str:
    serialized = "\n---PROMPT---\n".join(
        (bundle.initial, bundle.error or "", bundle.missing_coverage or "")
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
        package_dir = Path(getattr(config, "package_dir", ".")).resolve()
        project_root = Path(getattr(config, "project_root", ".")).resolve()
        for target in targets:
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
        # Schema 6 records zero-coverage batches when CoverUp accepts no tests.
        # Older caches incorrectly treated pytest's NO_TESTS_COLLECTED status as
        # an unusable evaluation and omitted all symbol denominators.
        "cache_schema": 6,
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
    raise KeyError(f"Target {wanted!r} is absent from cached batch {batch['run_id']}")


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
    """Evaluate all targets in one split with one CoverUp call and cache the batch."""
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
        record = runner.evaluate_batch(
            targets,
            candidate,
            candidate_id=run_candidate_id,
            split=split,
            workspace_kind=workspace_kind,
        )
        results = []
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
            })
        batch = {
            "prompt_digest": digest,
            "evaluation_digest": evaluation_digest,
            "replicate": replicate,
            "split": split,
            "workspace_kind": workspace_kind,
            "run_id": record.run_id,
            "generator_exit_code": int(getattr(record, "exit_code", 0) or 0),
            "tests_workspace": record.tests_workspace,
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
        "run_ids": [batch["run_id"] for batch in batches],
        "tests_workspaces": [batch["tests_workspace"] for batch in batches],
        "results": merged_results,
        "aggregate": aggregate,
        "batches": batches,
    }


def _find_source_path(runner: CoverUpExperimentRunner, target: SymbolTarget) -> Path | None:
    source = Path(target.source_file)
    candidates = (
        runner.config.package_dir.resolve().parent / source,
        runner.config.project_root.resolve() / source,
        runner.config.package_dir.resolve() / source.name,
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

    def _workspace_kind(self, bundle: PromptBundle) -> str:
        return "baseline" if bundle_digest(bundle) == self.baseline_digest else "candidate"

    def _remember_reference_units(self, results: list[dict]) -> None:
        for item in results:
            coverage = item.get("coverage")
            if coverage:
                self.reference_units[_result_identity(item)] = (
                    int(coverage["num_statements"]), int(coverage["num_branches"])
                )

    def _weighted_score(self, result: dict, full_results: list[dict]) -> float:
        self._remember_reference_units(full_results)
        identities = [_result_identity(item) for item in full_results]
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
        count = len(full_results)
        statement = (
            count * 0.4 * covered_statements / total_statements
            if total_statements else 0.4
        )
        branch = (
            count * 0.6 * covered_branches / total_branches
            if total_branches else 0.6
        )
        return statement + branch

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
        full_targets = self.targets_by_split[split]
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

        repeated_batches = [
            evaluate_bundle_batch_cached(
                self.runner,
                full_targets,
                bundle,
                self.candidate_dir,
                split=split,
                workspace_kind=self._workspace_kind(bundle),
                replicate=replicate,
            )
            for replicate in range(self.evaluation_replicates)
        ]
        lookups = [
            {_result_identity(result): result for result in record["results"]}
            for record in repeated_batches
        ]
        outputs = []
        scores = []
        objectives = []
        trajectories = [] if capture_traces else None
        for target in batch:
            identity = _target_identity(target)
            samples = [lookup[identity] for lookup in lookups]
            weighted_scores = [
                self._weighted_score(sample, record["results"])
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
                worst = min(samples, key=lambda item: float(item["score"]))
                trajectories.append({
                    "target": target.__dict__,
                    "score": raw_score,
                    "weighted_score": score,
                    "replicate_scores": raw_scores,
                    "feedback": worst["feedback"],
                    "coverage": worst.get("coverage"),
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
        weak_trajectories = [
            trajectory for trajectory in trajectories
            if float(trajectory.get("score", 0.0)) < 0.999999
        ] or list(trajectories)
        for component in components_to_update:
            placeholders = COMPONENT_PLACEHOLDERS[component]
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
                        "source_context": trajectory["source_context"],
                    },
                    "Generated Outputs": {
                        "symbol_score": trajectory["score"],
                        "replicate_scores": trajectory.get("replicate_scores", []),
                        "candidate_component_chars": len(candidate[component]),
                    },
                    "Feedback": (
                        f"{trajectory['feedback']}\n"
                        "Infer a reusable prompting improvement from this failure. "
                        "Do not embed project-specific names or line numbers in the template."
                    ),
                }
                for trajectory in weak_trajectories
            ]
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
            evidence = json.dumps(
                list(reflective_dataset.get(component, [])),
                indent=2,
                ensure_ascii=False,
            )
            placeholders = COMPONENT_PLACEHOLDERS[component]
            prompt = f"""You are optimizing one reusable CoverUp pytest-generation template.

Component: {component}
Role: {COMPONENT_ROLES[component]}
Required literal placeholders: {', '.join(placeholders)}
Maximum length: {self.max_component_chars[component]} characters

Current template:
<current_template>
{current}
</current_template>

Execution evidence from representative failing or weak targets:
<evidence>
{evidence}
</evidence>

Propose one conservative, generalizable improvement supported by the evidence. Preserve
useful behavior from the current template. Prefer precise operational guidance over long
checklists, repeated goals, score formulas, or generic claims. Never include target-specific
file names, symbols, or line numbers. Preserve every required placeholder exactly. Return
only the complete revised template between <template> and </template> tags.
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
        return proposals


def _optimization_run_digest(
    runner: CoverUpExperimentRunner,
    baseline: PromptBundle,
    train_targets: list[SymbolTarget],
    validation_targets: list[SymbolTarget],
    evaluation_replicates: int,
) -> str:
    payload = {
        "optimizer_schema": 6,
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
    """Optimize the actual three prompt templates with the baseline as candidate zero."""
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
        reflection_minibatch_size=min(3, len(train_targets)),
        module_selector="round_robin",
        use_merge=True,
        max_merge_invocations=5,
        max_metric_calls=max_metric_calls,
        run_dir=str(artifacts_dir / "gepa_direct_logs" / run_digest),
        cache_evaluation=True,
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
