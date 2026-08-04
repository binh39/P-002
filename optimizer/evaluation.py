from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any

from harness.runner import run_harness_on


@dataclass(frozen=True, slots=True)
class ModuleEvaluation:
    build_rate: float
    pass_rate: float
    statement_coverage: float
    branch_coverage: float
    mutation_score: float
    latency_seconds: float
    per_example: list[dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_module(module: Any, examples: Sequence[Any]) -> ModuleEvaluation:
    """Evaluate a DSPy module on one split through the common execution harness."""
    if not examples:
        raise ValueError("Cannot evaluate an empty split")
    started = time.monotonic()
    rows = []
    for example in examples:
        prediction = module(
            module_import=getattr(example, "module_import", ""),
            target_symbol=getattr(example, "target_symbol", ""),
            focal_code=example.focal_code,
            existing_tests=example.existing_tests,
            coverage_feedback=example.coverage_feedback,
        )
        harness_kwargs: dict[str, Any] = {}
        if mutation_target := getattr(example, "source_path", None):
            harness_kwargs["mutation_target"] = mutation_target
        if mutation_symbol := getattr(example, "symbol", None):
            harness_kwargs["mutation_symbol"] = mutation_symbol
        result = run_harness_on(
            example.module_path,
            prediction.test_code,
            **harness_kwargs,
        )
        rows.append(
            {
                "module_path": example.module_path,
                "result": result.as_dict(),
            }
        )
    count = len(rows)

    def mean(field: str) -> float:
        return sum(float(row["result"][field]) for row in rows) / count

    return ModuleEvaluation(
        build_rate=mean("build_ok"),
        pass_rate=mean("pass_rate"),
        statement_coverage=mean("statement_coverage"),
        branch_coverage=mean("branch_coverage"),
        mutation_score=mean("mutation_score"),
        latency_seconds=time.monotonic() - started,
        per_example=rows,
    )
