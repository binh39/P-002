import asyncio
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import gepa

from .executor import DockerCoverUpExecutor
from .prompts import PromptBundle


@dataclass(frozen=True, slots=True)
class OptimizationTarget:
    id: str
    symbol: str
    source: str
    split: str
    source_file: str = ""


@dataclass(frozen=True, slots=True)
class OptimizationResult:
    candidate: PromptBundle
    score: float
    baseline_score: float
    candidate_count: int
    metric_calls: int
    gepa_result: dict[str, Any]


class CoverUpGepaAdapter:
    def __init__(self, executor: DockerCoverUpExecutor, archive: bytes, source_directory: str):
        self.executor = executor
        self.archive = archive
        self.source_directory = source_directory
        runner = (
            executor.image,
            executor.timeout_seconds,
            executor.memory_mb,
            executor.cpu,
            executor.network_mode,
        )
        self.execution_fingerprint = (
            hashlib.sha256(archive).hexdigest(),
            source_directory,
            os.getenv("COVERUP_MODEL", ""),
            *runner,
        )
        self.cache: dict[tuple[Any, ...], dict[str, Any]] = {}

    def evaluate(self, batch, candidate, capture_traces=False):
        try:
            bundle = PromptBundle.from_candidate(candidate)
            bundle.validate()
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            trajectories = [{"feedback": str(exc), "source": item.source} for item in batch] if capture_traces else None
            return gepa.EvaluationBatch(
                outputs=[{} for _ in batch], scores=[0.0] * len(batch), trajectories=trajectories
            )

        outputs, scores = [], []
        trajectories = [] if capture_traces else None
        for target in batch:
            cache_key = (
                bundle.digest(),
                *self.execution_fingerprint,
                target.id,
                target.split,
                hashlib.sha256(target.source.encode()).hexdigest(),
            )
            cached = self.cache.get(cache_key)
            if cached is None:
                try:
                    execution = asyncio.run(
                        self.executor.execute(self.archive, self.source_directory, [target.symbol], bundle)
                    )
                    metric = execution.target_metrics.get(target.symbol, {})
                    trace = self._trace(execution.artifacts.get("attempt_trace.jsonl", b""))
                    cached = {"metric": metric, "trace": trace, "error": ""}
                except Exception as exc:
                    cached = {"metric": {"score": 0.0, "valid": False}, "trace": [], "error": str(exc)[-4000:]}
                self.cache[cache_key] = cached
            metric = cached["metric"]
            score = float(metric.get("score", 0.0)) if metric.get("valid") is not False else 0.0
            outputs.append({"target_id": target.id, "symbol": target.symbol, "coverage": metric})
            scores.append(score)
            if trajectories is not None:
                trajectories.append(
                    {
                        "target_id": target.id,
                        "symbol": target.symbol,
                        "source": target.source[:8000],
                        "coverage": metric,
                        "trace": cached["trace"][-4:],
                        "feedback": cached["error"] or self._feedback(metric),
                    }
                )
        return gepa.EvaluationBatch(outputs=outputs, scores=scores, trajectories=trajectories)

    def make_reflective_dataset(self, candidate, eval_batch, components_to_update):
        del candidate
        trajectories = eval_batch.trajectories or []
        return {
            component: [
                {
                    "Inputs": {"symbol": item["symbol"], "source": item["source"]},
                    "Generated Outputs": item["trace"],
                    "Feedback": item["feedback"],
                }
                for item in trajectories
            ]
            for component in components_to_update
        }

    @staticmethod
    def _trace(content: bytes) -> list[dict[str, Any]]:
        result = []
        for line in content.decode("utf-8", errors="replace").splitlines():
            try:
                result.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return result

    @staticmethod
    def _feedback(metric: dict[str, Any]) -> str:
        return (
            f"score={float(metric.get('score', 0.0)):.4f}; "
            f"statement={metric.get('covered_statements', 0)}/{metric.get('num_statements', 0)}; "
            f"branch={metric.get('covered_branches', 0)}/{metric.get('num_branches', 0)}"
        )


def optimize_prompt(
    *,
    executor: DockerCoverUpExecutor,
    archive: bytes,
    source_directory: str,
    baseline: PromptBundle,
    train: list[OptimizationTarget],
    validation: list[OptimizationTarget],
    reflection_model: str,
    max_metric_calls: int,
    holdout: list[OptimizationTarget] | None = None,
) -> OptimizationResult:
    del holdout
    if not train or not validation:
        raise ValueError("GEPA requires non-empty train and validation splits")
    baseline.validate()
    adapter = CoverUpGepaAdapter(executor, archive, source_directory)
    with tempfile.TemporaryDirectory(prefix="promptopt-gepa-") as run_dir:
        result = gepa.optimize(
            seed_candidate=baseline.as_candidate(),
            trainset=train,
            valset=validation,
            adapter=adapter,
            reflection_lm=reflection_model,
            candidate_selection_strategy="pareto",
            module_selector="round_robin",
            reflection_minibatch_size=min(4, len(train)),
            max_metric_calls=max_metric_calls,
            run_dir=str(Path(run_dir)),
            cache_evaluation=False,
            display_progress_bar=False,
            seed=7,
        )
    candidate = PromptBundle.from_candidate(result.best_candidate)
    candidate.validate()
    return OptimizationResult(
        candidate=candidate,
        score=float(result.val_aggregate_scores[result.best_idx]),
        baseline_score=float(result.val_aggregate_scores[0]),
        candidate_count=result.num_candidates,
        metric_calls=int(result.total_metric_calls or 0),
        gepa_result=result.to_dict(),
    )
