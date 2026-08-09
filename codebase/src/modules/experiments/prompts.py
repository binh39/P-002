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
    """Return the deliberately sparse seed prompt used for new experiments.

    GEPA needs room to discover useful instructions.  Keep this preset focused on
    the task and output shape; users that already have a stronger seed can submit
    their own validated bundle when creating an experiment.
    """
    return PromptBundle(
        initial="""Write pytest tests for {filename} that cover {coverage_targets}.
Return a complete test module in a Python markdown code block.

```python
{source_excerpt}
```""",
        error="""Fix the test error and return the complete Python test module:
{error}""",
    )
