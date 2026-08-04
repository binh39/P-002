from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SymbolTarget:
    project: str
    source_file: str
    symbol: str
    split: str = "train"

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> SymbolTarget:
        fields = cls.__dataclass_fields__
        return cls(**{key: value[key] for key in fields if key in value})


@dataclass
class ExperimentConfig:
    project_root: Path
    package_dir: Path
    tests_dir: Path
    artifacts_dir: Path
    coverup_model: str
    prompt_template_file: Path | None = None
    max_attempts: int = 3
    repeat_tests: int = 2
    max_concurrency: int = 10
    rate_limit: int | None = None
    pytest_args: str = ""


@dataclass
class RunRecord:
    run_id: str
    target: SymbolTarget
    command: list[str]
    started_at: str
    finished_at: str
    exit_code: int
    elapsed_seconds: float
    generated_tests: list[str] = field(default_factory=list)
    tests_workspace: str = ""
    coverage_before: str | None = None
    coverage_after: str | None = None
    score: dict[str, Any] | None = None
    feedback: str = ""
    stdout_file: str = ""
    coverup_log_file: str = ""
    attempt_trace_file: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BatchTargetResult:
    target: SymbolTarget
    score: dict[str, Any] | None = None
    feedback: str = ""
    attempt_traces: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BatchRunRecord:
    run_id: str
    split: str
    targets: list[SymbolTarget]
    command: list[str]
    started_at: str
    finished_at: str
    exit_code: int
    elapsed_seconds: float
    results: list[BatchTargetResult] = field(default_factory=list)
    generated_tests: list[str] = field(default_factory=list)
    tests_workspace: str = ""
    coverage_after: str | None = None
    stdout_file: str = ""
    coverup_log_file: str = ""
    attempt_trace_file: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
