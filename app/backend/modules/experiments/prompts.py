import hashlib
import json
from dataclasses import asdict, dataclass

DEFAULT_MISSING_COVERAGE_PROMPT = """The tests still lack coverage: {missing_coverage} not execute.
Modify the current test module to execute every remaining line and branch. Preserve passing
behavior and assertions, use get_info when more source context is needed, and return the
complete Python test module in a single Python markdown code block."""


@dataclass(frozen=True, slots=True)
class PromptBundle:
    initial: str
    error: str
    missing_coverage: str = DEFAULT_MISSING_COVERAGE_PROMPT

    def digest(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()[:16]

    def as_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    def as_candidate(self) -> dict[str, str]:
        return asdict(self)

    @classmethod
    def from_candidate(cls, candidate: dict[str, str]) -> "PromptBundle":
        required = {"initial", "error"}
        allowed = required | {"missing_coverage"}
        if not required.issubset(candidate) or not set(candidate).issubset(allowed):
            raise ValueError(
                "candidate must contain initial and error and may optionally contain "
                "the missing_coverage prompt component"
            )
        return cls(
            initial=candidate.get("initial", ""),
            error=candidate.get("error", ""),
            missing_coverage=(candidate.get("missing_coverage") or DEFAULT_MISSING_COVERAGE_PROMPT),
        )

    def validate(self) -> None:
        required = {
            "initial": ("{filename}", "{coverage_targets}", "{source_excerpt}"),
            "error": ("{error}",),
            "missing_coverage": ("{missing_coverage}",),
        }
        for name, placeholders in required.items():
            template = getattr(self, name)
            if not template or len(template.encode("utf-8")) > 32 * 1024:
                raise ValueError(f"{name} prompt must be between 1 byte and 32 KiB")
            if any(value not in template for value in placeholders):
                raise ValueError(f"{name} prompt is missing required placeholders")
            template.format(
                filename="x.py",
                coverage_targets="line 1",
                source_excerpt="pass",
                error="failed",
                missing_coverage="uncovered",
            )


def baseline_prompt() -> PromptBundle:
    """Return the deliberately sparse seed prompt used for new experiments."""
    return PromptBundle(
        initial="""Write pytest tests for {filename} that cover {coverage_targets}.
Use get_info(name) to inspect missing function, class, or method source/signatures; it follows
imports when possible. Do not guess APIs.
Return a complete test module in a Python markdown code block.

```python
{source_excerpt}
```""",
        error="""Fix the test error and return the complete Python test module.
Use get_info(name) for missing symbol details from the traceback before revising.
{error}""",
    )
