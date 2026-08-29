from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol


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


@dataclass(frozen=True)
class ProjectLayout:
    """Package and tests directories for one project of a multi-project run."""

    package_dir: Path
    tests_dir: Path
    import_root: Path | None = None
    python_executable: Path | None = None
    runtime_digest: str | None = None


@dataclass
class ExperimentConfig:
    project_root: Path
    package_dir: Path
    tests_dir: Path
    artifacts_dir: Path
    coverup_model: str
    prompt_template_file: Path | None = None
    max_attempts: int = 3
    repeat_tests: int = 5
    max_concurrency: int = 10
    rate_limit: int | None = None
    pytest_args: str = ""
    projects: dict[str, ProjectLayout] | None = None

    def package_dir_for(self, project: str) -> Path:
        """Resolve the package directory for ``project``.

        Falls back to the single-project ``package_dir`` when no per-project
        layout is configured.
        """
        if self.projects and project in self.projects:
            return self.projects[project].package_dir
        return self.package_dir

    def tests_dir_for(self, project: str) -> Path:
        """Resolve the tests directory for ``project``.

        Falls back to the single-project ``tests_dir`` when no per-project
        layout is configured.
        """
        if self.projects and project in self.projects:
            return self.projects[project].tests_dir
        return self.tests_dir

    def import_root_for(self, project: str) -> Path:
        """Return the PYTHONPATH root for the selected project layout."""
        if self.projects and project in self.projects:
            layout = self.projects[project]
            return layout.import_root or layout.package_dir.parent
        return self.package_dir.parent

    def python_for(self, project: str) -> Path | None:
        """Return the isolated interpreter assigned to one project runtime."""
        if self.projects and project in self.projects:
            return self.projects[project].python_executable
        return None


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

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> BatchTargetResult:
        return cls(
            target=SymbolTarget.from_dict(value["target"]),
            score=value.get("score"),
            feedback=str(value.get("feedback", "")),
            attempt_traces=list(value.get("attempt_traces", [])),
        )


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

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> BatchRunRecord:
        return cls(
            run_id=str(value["run_id"]),
            split=str(value["split"]),
            targets=[SymbolTarget.from_dict(item) for item in value.get("targets", [])],
            command=[str(item) for item in value.get("command", [])],
            started_at=str(value.get("started_at", "")),
            finished_at=str(value.get("finished_at", "")),
            exit_code=int(value.get("exit_code", 0) or 0),
            elapsed_seconds=float(value.get("elapsed_seconds", 0.0) or 0.0),
            results=[BatchTargetResult.from_dict(item) for item in value.get("results", [])],
            generated_tests=[str(item) for item in value.get("generated_tests", [])],
            tests_workspace=str(value.get("tests_workspace", "")),
            coverage_after=value.get("coverage_after"),
            stdout_file=str(value.get("stdout_file", "")),
            coverup_log_file=str(value.get("coverup_log_file", "")),
            attempt_trace_file=str(value.get("attempt_trace_file", "")),
        )


class EvaluationBackend(Protocol):
    """Execution boundary between GEPA and project-specific test workers."""

    def evaluate_batch(
        self,
        targets: list[SymbolTarget],
        prompt_template: Path,
        *,
        candidate_id: str | None,
        split: str | None,
        workspace_kind: str,
    ) -> BatchRunRecord: ...

    def evaluate_optimizer_test(
        self,
        target: SymbolTarget,
        test_module: str,
        *,
        experiment_id: str,
    ) -> dict[str, Any]: ...
