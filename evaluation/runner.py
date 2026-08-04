from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from harness.models import HarnessResult
from harness.runner import run_harness_on

from .ledger import HoldoutLedger, holdout_digest
from .models import BaselineEvaluation, GeneratedTest


def _failed_result(error: Exception) -> HarnessResult:
    return HarnessResult(
        build_ok=False,
        build_error=str(error)[-4000:],
        num_tests=0,
        num_passed=0,
        pass_rate=0.0,
        statement_coverage=0.0,
        branch_coverage=0.0,
        mutation_score=0.0,
    )


def _write_checkpoint(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary.replace(path)


def evaluate_generator(
    name: str,
    generator: Callable[[Any], GeneratedTest],
    holdout: list[Any],
    *,
    result_file: str | Path,
    ledger: HoldoutLedger,
    initial_cost_usd: float = 0.0,
    initial_latency_seconds: float = 0.0,
) -> BaselineEvaluation:
    """Evaluate one baseline exactly once on the locked held-out examples."""
    if not holdout:
        raise ValueError("Held-out evaluation requires at least one example")
    digest = holdout_digest(holdout)
    ledger.assert_available(name, digest)
    destination = Path(result_file)
    checkpoint = destination.with_suffix(destination.suffix + ".partial")
    if destination.exists():
        raise RuntimeError(
            f"Result file already exists without a completed ledger entry: {destination}"
        )
    if initial_cost_usd < 0 or initial_latency_seconds < 0:
        raise ValueError("Initial cost and latency must be non-negative")
    rows: list[dict[str, Any]] = []
    total_cost = initial_cost_usd
    total_latency = initial_latency_seconds
    if checkpoint.exists():
        saved = json.loads(checkpoint.read_text(encoding="utf-8"))
        if saved.get("name") != name or saved.get("holdout_digest") != digest:
            raise RuntimeError("Partial evaluation does not match this baseline/holdout")
        rows = list(saved.get("rows", []))
        total_cost = float(saved.get("total_cost", 0.0))
        total_latency = float(saved.get("total_latency", 0.0))
    completed_ids = {row["example_id"] for row in rows}

    for index, example in enumerate(holdout):
        example_id = getattr(example, "example_id", str(index))
        if example_id in completed_ids:
            continue
        try:
            generated = generator(example)
            harness_kwargs: dict[str, Any] = {}
            if mutation_target := getattr(example, "source_path", None):
                harness_kwargs["mutation_target"] = mutation_target
            if mutation_symbol := getattr(example, "symbol", None):
                harness_kwargs["mutation_symbol"] = mutation_symbol
            result = run_harness_on(
                example.module_path,
                generated.test_code,
                **harness_kwargs,
            )
        except Exception as exc:
            generated = GeneratedTest(test_code="")
            result = _failed_result(exc)
        total_cost += generated.cost_usd
        total_latency += generated.latency_seconds + result.duration_seconds
        rows.append(
            {
                "example_id": example_id,
                "result": result.as_dict(),
                "test_code": generated.test_code,
                "cost_usd": generated.cost_usd,
                "latency_seconds": generated.latency_seconds
                + result.duration_seconds,
            }
        )
        _write_checkpoint(
            checkpoint,
            {
                "name": name,
                "holdout_digest": digest,
                "rows": rows,
                "total_cost": total_cost,
                "total_latency": total_latency,
            },
        )
    count = len(rows)

    def mean(field: str) -> float:
        return sum(float(row["result"][field]) for row in rows) / count

    evaluation = BaselineEvaluation(
        name=name,
        build_rate=mean("build_ok"),
        pass_rate=mean("pass_rate"),
        statement_coverage=mean("statement_coverage"),
        branch_coverage=mean("branch_coverage"),
        mutation_score=mean("mutation_score"),
        cost_usd=total_cost,
        latency_seconds=total_latency,
        holdout_digest=digest,
        per_example=rows,
    )
    evaluation.save(destination)
    ledger.complete(name, digest, result_file)
    checkpoint.unlink(missing_ok=True)
    return evaluation
