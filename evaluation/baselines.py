from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import dspy

from optimizer.signatures import GenerateUnitTest

from .models import GeneratedTest

ZERO_SHOT_INSTRUCTIONS = (
    "Write a complete pytest unit test module for the supplied focal code. "
    "Import the target from module_import; never use a placeholder module name. "
    "Return only executable test code."
)

SYMPROMPT_INSTRUCTIONS = (
    "Write a complete deterministic pytest module. First identify each distinct "
    "execution path and boundary condition in the focal code, then create a focused "
    "test for every path. Cover true and false branches, empty and boundary inputs, "
    "and documented exceptions. Use meaningful assertions and pytest monkeypatch "
    "fixtures for all state changes. Import the target from module_import and never "
    "use a placeholder module name. Return only executable test code."
)


def normalize_test_code(value: Any) -> str:
    """Return executable Python when an LM wraps its answer in Markdown."""
    text = value if isinstance(value, str) else str(value or "")
    match = re.search(r"```(?:python|py)?\s*\n(.*?)(?:\n```|\Z)", text, re.DOTALL)
    return (match.group(1) if match else text).strip() + "\n"


class FixedPromptModule(dspy.Module):
    def __init__(self, instructions: str):
        super().__init__()
        self.predict = dspy.Predict(
            GenerateUnitTest.with_instructions(instructions)
        )

    def forward(
        self,
        focal_code: str,
        existing_tests: str = "",
        coverage_feedback: str = "",
        module_import: str = "",
        target_symbol: str = "",
    ):
        return self.predict(
            module_import=module_import,
            target_symbol=target_symbol,
            focal_code=focal_code,
            existing_tests=existing_tests,
            coverage_feedback=coverage_feedback,
        )


def zero_shot_module() -> FixedPromptModule:
    return FixedPromptModule(ZERO_SHOT_INSTRUCTIONS)


def static_symprompt_module() -> FixedPromptModule:
    return FixedPromptModule(SYMPROMPT_INSTRUCTIONS)


class DspyModuleGenerator:
    def __init__(
        self,
        module: dspy.Module,
        *,
        cumulative_cost: Callable[[], float] | None = None,
    ):
        self.module = module
        self.cumulative_cost = cumulative_cost or (lambda: 0.0)

    def __call__(self, example: Any) -> GeneratedTest:
        before_cost = self.cumulative_cost()
        started = time.monotonic()
        prediction = self.module(
            module_import=getattr(example, "module_import", ""),
            target_symbol=getattr(example, "target_symbol", ""),
            focal_code=example.focal_code,
            existing_tests=example.existing_tests,
            coverage_feedback=example.coverage_feedback,
        )
        return GeneratedTest(
            test_code=normalize_test_code(prediction.test_code),
            cost_usd=max(0.0, self.cumulative_cost() - before_cost),
            latency_seconds=time.monotonic() - started,
        )


class CoverUpManifestGenerator:
    """Load CoverUp outputs from an explicit example-id → test-file manifest."""

    def __init__(self, manifest_path: str | Path):
        manifest_file = Path(manifest_path)
        raw = json.loads(manifest_file.read_text(encoding="utf-8"))
        self.tests = {
            key: (manifest_file.parent / value).resolve()
            for key, value in raw.items()
        }

    def __call__(self, example: Any) -> GeneratedTest:
        example_id = example.example_id
        if example_id not in self.tests:
            raise KeyError(f"CoverUp manifest has no test for {example_id}")
        return GeneratedTest(
            test_code=normalize_test_code(
                self.tests[example_id].read_text(encoding="utf-8")
            )
        )


class CoverUpDirectoryGenerator:
    """Remeasure a complete test suite emitted by a real CoverUp CLI run."""

    def __init__(self, tests_dir: str | Path):
        directory = Path(tests_dir)
        files = sorted(directory.glob("test_*.py"))
        if not files:
            raise ValueError(f"No CoverUp test_*.py files found in {directory}")
        self.test_code = "\n\n".join(
            file.read_text(encoding="utf-8").strip() for file in files
        ) + "\n"

    def __call__(self, example: Any) -> GeneratedTest:
        del example
        return GeneratedTest(test_code=self.test_code)
