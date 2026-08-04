from __future__ import annotations

import dspy


class GenerateUnitTest(dspy.Signature):
    """Generate reliable pytest tests for the exact importable target.

    Import the symbol under test from ``module_import``. Never invent or use
    placeholder module names such as ``your_module``.
    """

    module_import: str = dspy.InputField(
        desc="Real dotted Python module to import in the generated pytest module"
    )
    target_symbol: str = dspy.InputField(
        desc="Qualified function, method, or class symbol under test"
    )
    focal_code: str = dspy.InputField(desc="Source of the function or class under test")
    existing_tests: str = dspy.InputField(desc="Existing tests, possibly empty")
    coverage_feedback: str = dspy.InputField(
        desc="Uncovered lines and branches reported by the execution harness"
    )
    test_code: str = dspy.OutputField(
        desc="A complete deterministic pytest module that can run directly"
    )
