import hashlib
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class PromptBundle:
    initial: str
    error: str

    def digest(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()[:16]

    def as_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    def validate(self) -> None:
        required = {"initial": ("{filename}", "{coverage_targets}", "{source_excerpt}"), "error": ("{error}",)}
        for name, placeholders in required.items():
            template = getattr(self, name)
            if any(value not in template for value in placeholders):
                raise ValueError(f"{name} prompt is missing required placeholders")
            template.format(filename="x.py", coverage_targets="line 1", source_excerpt="pass", error="failed")


def baseline_prompt() -> PromptBundle:
    return PromptBundle(
        initial="""You are an expert Python test-driven developer.
The code below, extracted from {filename}, does not achieve full coverage:
when tested, {coverage_targets} do not execute.
Create new pytest tests that execute all missing lines and branches. Tests must be deterministic,
use meaningful assertions, clean up modified state, and return a complete Python test module only.
Do not call pytest.main or execute tests at module import time.

```python
{source_excerpt}
```""",
        error="""Executing the generated test produced this error:
{error}
Rewrite the complete pytest module to fix the error. Preserve useful assertions and return only Python code.""",
    )
