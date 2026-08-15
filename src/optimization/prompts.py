from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class PromptBundle:
    initial: str
    error: str | None = None

    @classmethod
    def load(cls, path: Path) -> PromptBundle:
        with path.open(encoding="utf-8") as file:
            values = json.load(file)
        # Select active fields explicitly so legacy prompt keys are harmless.
        return cls(initial=values["initial"], error=values.get("error"))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        values = {key: value for key, value in asdict(self).items() if value is not None}
        path.write_text(json.dumps(values, indent=2, ensure_ascii=False), encoding="utf-8")

    def as_candidate(self) -> dict[str, str]:
        """Return the direct GEPA component mapping for this prompt bundle."""
        if self.error is None:
            raise ValueError("A GEPA candidate requires initial and error prompts")
        return {
            "initial": self.initial,
            "error": self.error,
        }

    @classmethod
    def from_candidate(cls, candidate: dict[str, str]) -> PromptBundle:
        """Build a prompt bundle from a direct GEPA component mapping."""
        return cls(
            initial=candidate.get("initial", ""),
            error=candidate.get("error", ""),
        )


BASELINE_INITIAL = """You are an expert Python test-driven developer.
The code below, extracted from {filename}, does not achieve full coverage:
when tested, {coverage_targets} not execute.
Create new pytest test functions that execute all missing lines and branches. Each test must
be correct, deterministic, contain meaningful assertions, and clean up all modified state.
Prefer several small, independent test_* functions over one large function with many sequential
inline scenarios: an early failure inside a shared function blocks coverage measurement of every
later scenario. If a target is best covered by many scenarios, split them into separate test
functions so an isolated failure does not discard the rest.
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

def baseline_bundle() -> PromptBundle:
    return PromptBundle(
        initial=BASELINE_INITIAL,
        error=BASELINE_ERROR,
    )
