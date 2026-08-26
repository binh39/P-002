from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class PromptBundle:
    initial: str
    error: str | None = None
    missing_coverage: str | None = None

    @classmethod
    def load(cls, path: Path) -> PromptBundle:
        with path.open(encoding="utf-8") as file:
            values = json.load(file)
        # Select active fields explicitly so legacy prompt keys are harmless.
        return cls(
            initial=values["initial"],
            error=values.get("error"),
            missing_coverage=values.get("missing_coverage", BASELINE_MISSING_COVERAGE),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")

    def as_candidate(self) -> dict[str, str]:
        """Return the direct GEPA component mapping for this prompt bundle."""
        if self.error is None:
            raise ValueError("A GEPA candidate requires initial and error prompts")
        return {
            "initial": self.initial,
            "error": self.error,
            "missing_coverage": self.missing_coverage if self.missing_coverage is not None else BASELINE_MISSING_COVERAGE,
        }

    @classmethod
    def from_candidate(cls, candidate: dict[str, str]) -> PromptBundle:
        """Build a prompt bundle from a direct GEPA component mapping."""
        return cls(
            initial=candidate.get("initial", ""),
            error=candidate.get("error", ""),
            missing_coverage=candidate.get("missing_coverage", BASELINE_MISSING_COVERAGE),
        )


BASELINE_INITIAL = """You are an expert Python test-driven developer.
The code below, extracted from {filename}, does not achieve full coverage:
when tested, {coverage_targets} not execute.
Create new pytest test functions that execute all missing lines and branches. Each test must
be correct, deterministic, contain meaningful assertions, and clean up all modified state.
Use the get_info tool function as necessary. Always return an entire Python test module.
Do not call pytest.main and do not execute tests at module import time.
Respond only with Python code enclosed in a python markdown code block.

```python
{source_excerpt}
```"""

BASELINE_ERROR = """Executing the test yields an error, shown below.
Modify or rewrite the test to correct it. Return the complete Python test module, not a patch.
Preserve useful assertions from the previous test and use get_info when more source context is needed.
Respond only with Python code enclosed in a python markdown code block.

{error}"""

BASELINE_MISSING_COVERAGE = """The tests still lack coverage: {missing_coverage} not execute.
Modify the current test module to execute every remaining line and branch. Preserve passing
behavior and assertions, use get_info when more source context is needed, and return the
complete Python test module in a single Python markdown code block."""

def baseline_bundle() -> PromptBundle:
    return PromptBundle(
        initial=BASELINE_INITIAL,
        error=BASELINE_ERROR,
        missing_coverage=BASELINE_MISSING_COVERAGE,
    )
