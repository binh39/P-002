from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True, slots=True)
class HarnessResult:
    """Stable result contract shared by optimizers, APIs, and reports."""

    build_ok: bool
    build_error: str
    num_tests: int
    num_passed: int
    pass_rate: float
    statement_coverage: float
    branch_coverage: float
    mutation_score: float
    surviving_mutant_lines: list[int] = field(default_factory=list)
    duration_seconds: float = 0.0

    def __post_init__(self) -> None:
        if self.num_tests < 0 or self.num_passed < 0:
            raise ValueError("Test counts must be non-negative")
        if self.num_passed > self.num_tests:
            raise ValueError("num_passed cannot exceed num_tests")
        for name in (
            "pass_rate",
            "statement_coverage",
            "branch_coverage",
            "mutation_score",
        ):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.duration_seconds < 0:
            raise ValueError("duration_seconds must be non-negative")

    def as_dict(self) -> dict:
        return asdict(self)
