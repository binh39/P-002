import asyncio
import time
from dataclasses import asdict, dataclass

from .executor import DockerCoverUpExecutor
from .optimizer import OptimizationTarget
from .prompts import PromptBundle


@dataclass(frozen=True, slots=True)
class EvaluationSample:
    target_id: str
    symbol: str
    replicate: int
    valid: bool
    score: float
    covered_statements: int
    num_statements: int
    covered_branches: int
    num_branches: int
    statement_coverage: float | None
    branch_coverage: float | None
    latency_seconds: float
    timed_out: bool = False
    error: str = ""


@dataclass(frozen=True, slots=True)
class FinalComparison:
    baseline: dict
    candidate: dict
    absolute_gain: float
    relative_gain: float | None
    promotion_eligible: bool
    decision_reason: str
    paired_deltas: list[dict]
    samples: dict[str, list[dict]]

    def as_dict(self) -> dict:
        return asdict(self)


async def compare_prompts(
    *,
    executor: DockerCoverUpExecutor,
    archive: bytes,
    source_directory: str,
    targets: list[OptimizationTarget],
    baseline: PromptBundle,
    candidate: PromptBundle,
    replicates: int,
) -> FinalComparison:
    if not targets:
        raise ValueError("Final comparison requires a non-empty locked test split")
    if replicates < 1:
        raise ValueError("Final comparison requires at least one replicate")
    baseline.validate()
    candidate.validate()
    if baseline.digest() == candidate.digest():
        return FinalComparison(
            baseline={},
            candidate={},
            absolute_gain=0.0,
            relative_gain=0.0,
            promotion_eligible=False,
            decision_reason="Candidate is identical to the baseline prompt; final evaluation was skipped",
            paired_deltas=[],
            samples={"baseline": [], "candidate": []},
        )

    baseline_samples = await _evaluate(executor, archive, source_directory, targets, baseline, replicates)
    candidate_samples = await _evaluate(executor, archive, source_directory, targets, candidate, replicates)
    baseline_metrics = _aggregate(baseline_samples)
    candidate_metrics = _aggregate(candidate_samples)
    paired_deltas = [
        {
            "target_id": baseline_sample.target_id,
            "replicate": baseline_sample.replicate,
            "score": candidate_sample.score - baseline_sample.score,
            "statement_coverage": _difference(candidate_sample.statement_coverage, baseline_sample.statement_coverage),
            "branch_coverage": _difference(candidate_sample.branch_coverage, baseline_sample.branch_coverage),
        }
        for baseline_sample, candidate_sample in zip(baseline_samples, candidate_samples, strict=True)
    ]
    absolute_gain = sum(delta["score"] for delta in paired_deltas) / len(paired_deltas)
    relative_gain = absolute_gain / baseline_metrics["score"] if baseline_metrics["score"] else None

    reason = _promotion_reason(baseline_metrics, candidate_metrics, absolute_gain)
    return FinalComparison(
        baseline=baseline_metrics,
        candidate=candidate_metrics,
        absolute_gain=absolute_gain,
        relative_gain=relative_gain,
        promotion_eligible=not reason,
        decision_reason=reason or "Candidate improved locked-test coverage and passed all hard gates",
        paired_deltas=paired_deltas,
        samples={
            "baseline": [asdict(sample) for sample in baseline_samples],
            "candidate": [asdict(sample) for sample in candidate_samples],
        },
    )


async def _evaluate(executor, archive, source_directory, targets, prompt, replicates):
    samples = []
    for target in targets:
        for replicate in range(replicates):
            started = time.perf_counter()
            try:
                result = await executor.execute(archive, source_directory, [target.symbol], prompt)
                metric = result.target_metrics.get(target.symbol, {})
                valid = bool(metric.get("valid"))
                samples.append(
                    EvaluationSample(
                        target_id=target.id,
                        symbol=target.symbol,
                        replicate=replicate,
                        valid=valid,
                        score=float(metric.get("score", 0.0)) if valid else 0.0,
                        covered_statements=int(metric.get("covered_statements", 0)) if valid else 0,
                        num_statements=int(metric.get("num_statements", 0)) if valid else 0,
                        covered_branches=int(metric.get("covered_branches", 0)) if valid else 0,
                        num_branches=int(metric.get("num_branches", 0)) if valid else 0,
                        statement_coverage=metric.get("statement_coverage") if valid else None,
                        branch_coverage=metric.get("branch_coverage") if valid else None,
                        latency_seconds=time.perf_counter() - started,
                    )
                )
            except Exception as exc:
                samples.append(
                    EvaluationSample(
                        target_id=target.id,
                        symbol=target.symbol,
                        replicate=replicate,
                        valid=False,
                        score=0.0,
                        covered_statements=0,
                        num_statements=0,
                        covered_branches=0,
                        num_branches=0,
                        statement_coverage=None,
                        branch_coverage=None,
                        latency_seconds=time.perf_counter() - started,
                        timed_out=isinstance(exc, (TimeoutError, asyncio.TimeoutError))
                        or "timed out" in str(exc).lower(),
                        error=str(exc)[-1000:],
                    )
                )
    return samples


def _aggregate(samples: list[EvaluationSample]) -> dict:
    valid = [sample for sample in samples if sample.valid]
    scores_by_target: dict[str, list[float]] = {}
    for sample in samples:
        scores_by_target.setdefault(sample.target_id, []).append(sample.score)
    flaky_targets = [
        target_id
        for target_id, scores in scores_by_target.items()
        if max(scores, default=0.0) - min(scores, default=0.0) > 0.05
    ]
    covered_statements = sum(sample.covered_statements for sample in valid)
    num_statements = sum(sample.num_statements for sample in valid)
    covered_branches = sum(sample.covered_branches for sample in valid)
    num_branches = sum(sample.num_branches for sample in valid)
    return {
        "score": sum(sample.score for sample in samples) / len(samples),
        "statement_coverage": covered_statements / num_statements if num_statements else None,
        "branch_coverage": covered_branches / num_branches if num_branches else None,
        "pass_rate": len(valid) / len(samples),
        "latency_seconds": sum(sample.latency_seconds for sample in samples),
        "sample_count": len(samples),
        "timeout_count": sum(sample.timed_out for sample in samples),
        "flaky_targets": flaky_targets,
    }


def _promotion_reason(baseline: dict, candidate: dict, absolute_gain: float) -> str:
    if candidate["timeout_count"]:
        return "Candidate timed out during locked-test evaluation"
    if candidate["pass_rate"] < 1:
        return "Candidate did not produce valid passing tests for every evaluation sample"
    if candidate["pass_rate"] < baseline["pass_rate"]:
        return "Candidate reduced the generated-test pass rate"
    if candidate["flaky_targets"]:
        return "Candidate coverage varied across replicates"
    if absolute_gain <= 0:
        return "Candidate did not improve locked-test coverage"
    return ""


def _difference(candidate: float | None, baseline: float | None) -> float | None:
    if candidate is None or baseline is None:
        return None
    return candidate - baseline
