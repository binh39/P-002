from __future__ import annotations

from pathlib import Path

import dspy

from .signatures import GenerateUnitTest
from .tools import check_coverage_gaps, run_test_draft


class TestGenReactModule(dspy.Module):
    """Coverage-guided ReAct module whose instructions can be compiled by DSPy."""

    def __init__(
        self,
        module_path: str | Path,
        max_iters: int = 4,
        *,
        instructions: str | None = None,
    ):
        super().__init__()
        if max_iters < 1:
            raise ValueError("max_iters must be at least 1")
        self.module_path = str(Path(module_path).resolve())
        self.max_iters = max_iters
        signature = (
            GenerateUnitTest.with_instructions(instructions)
            if instructions
            else GenerateUnitTest
        )
        self.agent = dspy.ReAct(
            signature,
            tools=[self.check_coverage_gaps, self.run_test_draft],
            max_iters=max_iters,
        )

    def check_coverage_gaps(self, current_test_code: str) -> str:
        """Check uncovered paths for a proposed pytest module."""
        return check_coverage_gaps(self.module_path, current_test_code)

    def run_test_draft(self, test_code: str) -> str:
        """Run a proposed pytest module and report pass/coverage evidence."""
        return run_test_draft(self.module_path, test_code)

    def forward(
        self,
        focal_code: str,
        existing_tests: str = "",
        coverage_feedback: str = "",
        module_import: str = "",
        target_symbol: str = "",
    ):
        return self.agent(
            module_import=module_import,
            target_symbol=target_symbol,
            focal_code=focal_code,
            existing_tests=existing_tests,
            coverage_feedback=coverage_feedback,
        )
