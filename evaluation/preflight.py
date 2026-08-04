from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from typing import Any

from harness.runner import run_harness_on

from .models import GeneratedTest

_PLACEHOLDER_IMPORT = re.compile(
    r"(?m)^\s*(?:from|import)\s+"
    r"(?:your_module|module_name|my_module|mymodule|the_module)\b"
)


def validate_generation_contract(
    generator: Callable[[Any], GeneratedTest],
    validation: Sequence[Any],
) -> tuple[float, float]:
    """Fail before optimization/held-out use when generated imports are unusable."""
    if not validation:
        raise ValueError("Generation preflight requires validation examples")

    # A short focal target keeps this infrastructure check bounded and
    # deterministic while still exercising the real provider and Docker harness.
    example = min(
        validation,
        key=lambda item: (len(item.focal_code), item.example_id),
    )
    generated = generator(example)
    if _PLACEHOLDER_IMPORT.search(generated.test_code):
        raise RuntimeError(
            "Generation preflight produced a placeholder module import for "
            f"{example.example_id}. The optimizer was stopped before held-out use."
        )

    result = run_harness_on(
        example.module_path,
        generated.test_code,
        run_mutation=False,
        mutation_target=getattr(example, "source_path", None),
        mutation_symbol=getattr(example, "symbol", None),
    )
    if not result.build_ok or result.num_tests < 1:
        detail = result.build_error.strip().splitlines()
        suffix = detail[-1] if detail else "pytest collected no tests"
        raise RuntimeError(
            "Generation preflight could not collect a real pytest test for "
            f"{example.example_id}: {suffix}"
        )
    return generated.cost_usd, generated.latency_seconds + result.duration_seconds
