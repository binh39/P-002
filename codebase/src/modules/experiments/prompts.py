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

    def as_candidate(self) -> dict[str, str]:
        return asdict(self)

    @classmethod
    def from_candidate(cls, candidate: dict[str, str]) -> "PromptBundle":
        if set(candidate) != {"initial", "error"}:
            raise ValueError("candidate may only contain the initial and error prompt components")
        return cls(initial=candidate.get("initial", ""), error=candidate.get("error", ""))

    def validate(self) -> None:
        required = {"initial": ("{filename}", "{coverage_targets}", "{source_excerpt}"), "error": ("{error}",)}
        for name, placeholders in required.items():
            template = getattr(self, name)
            if not template or len(template.encode("utf-8")) > 32 * 1024:
                raise ValueError(f"{name} prompt must be between 1 byte and 32 KiB")
            if any(value not in template for value in placeholders):
                raise ValueError(f"{name} prompt is missing required placeholders")
            template.format(filename="x.py", coverage_targets="line 1", source_excerpt="pass", error="failed")


def baseline_prompt() -> PromptBundle:
    return PromptBundle(
        initial="""You are an expert Python test-driven developer.
The code below, extracted from {filename}, does not achieve full coverage:
when tested, {coverage_targets} not execute.
Create new pytest test functions that execute all missing lines and branches. Each test must
be correct, deterministic, contain meaningful assertions, and clean up all modified state.
Use the get_info tool function as necessary. Always return an entire Python test module.
Do not call pytest.main and do not execute tests at module import time.
Respond only with Python code enclosed in a python markdown code block.

```python
{source_excerpt}
```""",
        error="""Executing the test yields an error, shown below.
Modify or rewrite the test to correct it. Return the complete Python test module, not a patch.
Preserve useful assertions from the previous test and use get_info when more source context is needed.
Respond only with Python code enclosed in a python markdown code block.

{error}""",
    )
