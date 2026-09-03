"""Bridge optimizer evaluations to immutable project sandbox artifacts."""

from __future__ import annotations

import ast
import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from cloud.sandbox_builder import ArtifactManifest
from cloud.sandbox_contract import (
    CoverageMode,
    DependencyMode,
    DependencyPolicy,
    ResourceLimits,
    RunKind,
    RunnerProfile,
    RunSpec,
    SandboxResult,
    SandboxSpec,
    require_matching_fingerprint,
)
from cloud.sandbox_executor import DockerExecutionRequest, DockerSandboxExecutor

from .coveragepy import SymbolCoverage
from .models import SandboxEnvironment, SymbolTarget


class SandboxEvaluationError(RuntimeError):
    """Raised when an evaluation cannot produce a trustworthy scoring input."""


@dataclass(frozen=True)
class SandboxEvaluation:
    result: SandboxResult
    coverage: SymbolCoverage | None


class _SymbolRanges(ast.NodeVisitor):
    def __init__(self) -> None:
        self.stack: list[str] = []
        self.ranges: dict[str, tuple[int, int]] = {}

    def _visit(self, node) -> None:
        self.stack.append(node.name)
        self.ranges[".".join(self.stack)] = (node.lineno, node.end_lineno or node.lineno)
        self.generic_visit(node)
        self.stack.pop()

    def visit_FunctionDef(self, node) -> None:  # noqa: N802 - ast.NodeVisitor API
        self._visit(node)

    def visit_AsyncFunctionDef(self, node) -> None:  # noqa: N802 - ast.NodeVisitor API
        self._visit(node)

    def visit_ClassDef(self, node) -> None:  # noqa: N802 - ast.NodeVisitor API
        self._visit(node)


def _manifest(environment: SandboxEnvironment) -> ArtifactManifest:
    try:
        return ArtifactManifest.from_dict(
            json.loads(environment.artifact_manifest.read_text(encoding="utf-8"))
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise SandboxEvaluationError("Project sandbox manifest is invalid") from exc


def _source_path(environment: SandboxEnvironment, target: SymbolTarget) -> Path:
    root = environment.source_root.resolve()
    path = (root / Path(*target.source_file.replace("\\", "/").split("/"))).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise SandboxEvaluationError("Target source_file escapes its project source root") from exc
    if not path.is_file():
        raise SandboxEvaluationError(f"Target source file does not exist: {target.source_file}")
    return path


def _copy_test_inputs(
    test_paths: list[Path],
    project_tests: Path,
    destination: Path,
    *,
    repeats: int,
) -> list[str]:
    if repeats < 1:
        raise SandboxEvaluationError("Sandbox test repeat count must be positive")
    destination.mkdir(parents=True, exist_ok=False)
    selected: list[str] = []
    for index, source in enumerate(test_paths, start=1):
        source = source.resolve()
        if not source.is_file():
            raise SandboxEvaluationError(f"Generated test does not exist: {source}")
        for replicate in range(repeats):
            target = destination / f"test_generated_{index:04d}_r{replicate:04d}.py"
            shutil.copyfile(source, target)
            selected.append(target.name)
    conftest = project_tests.resolve() / "conftest.py"
    if conftest.is_file():
        shutil.copyfile(conftest, destination / "conftest.py")
    return selected


def _normalized_symbol_coverage(
    path: Path,
    *,
    environment: SandboxEnvironment,
    target: SymbolTarget,
    result: SandboxResult,
) -> SymbolCoverage:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("environment_fingerprint") != result.environment_fingerprint:
        raise SandboxEvaluationError("Coverage artifact fingerprint does not match SandboxResult")
    if payload.get("target") != {"source_file": target.source_file, "symbol": target.symbol}:
        raise SandboxEvaluationError("Coverage artifact target identity does not match the requested symbol")
    source = _source_path(environment, target)
    visitor = _SymbolRanges()
    visitor.visit(ast.parse(source.read_text(encoding="utf-8"), filename=str(source)))
    if target.symbol not in visitor.ranges:
        raise SandboxEvaluationError("Requested symbol is absent from its source file")
    first, last = visitor.ranges[target.symbol]
    records = [item for item in payload.get("files", []) if item.get("path") == target.source_file]
    if len(records) != 1 or result.coverage is None:
        raise SandboxEvaluationError("Normalized coverage does not contain one exact target source")
    record = records[0]
    executed_lines = tuple(sorted(int(line) for line in record["executed_lines"] if first <= int(line) <= last))
    missing_lines = tuple(sorted(int(line) for line in record["missing_lines"] if first <= int(line) <= last))

    def branches(name: str) -> tuple[tuple[int, int], ...]:
        return tuple(
            sorted(
                (int(item[0]), int(item[1]))
                for item in record[name]
                if isinstance(item, list) and len(item) == 2 and first <= int(item[0]) <= last
            )
        )

    summary = result.coverage
    return SymbolCoverage(
        source_file=target.source_file,
        symbol=target.symbol,
        covered_statements=summary.covered_statements,
        num_statements=summary.total_statements,
        covered_branches=summary.covered_branches,
        num_branches=summary.total_branches,
        executed_lines=executed_lines,
        missing_lines=missing_lines,
        executed_branches=branches("executed_branches"),
        missing_branches=branches("missing_branches"),
    )


class OptimizerSandboxClient:
    """Execute generated tests without importing project dependencies into the optimizer."""

    def __init__(
        self,
        environments: dict[str, SandboxEnvironment],
        *,
        executor: DockerSandboxExecutor | None = None,
    ) -> None:
        if not environments:
            raise ValueError("At least one project sandbox environment is required")
        self.environments = environments
        self.executor = executor or DockerSandboxExecutor()

    def fingerprint_for(self, project: str) -> str:
        try:
            environment = self.environments[project]
        except KeyError as exc:
            raise SandboxEvaluationError(f"No sandbox environment is configured for project {project!r}") from exc
        return _manifest(environment).fingerprint

    def fingerprints_for(self, projects: set[str]) -> dict[str, str]:
        return {project: self.fingerprint_for(project) for project in sorted(projects)}

    def evaluate(
        self,
        target: SymbolTarget,
        test_paths: list[Path],
        *,
        project_tests: Path,
        run_root: Path,
        run_id: str,
        kind: RunKind,
        repeat_tests: int = 1,
    ) -> SandboxEvaluation:
        try:
            environment = self.environments[target.project]
        except KeyError as exc:
            raise SandboxEvaluationError(f"No sandbox environment is configured for project {target.project!r}") from exc
        manifest = _manifest(environment)
        source = _source_path(environment, target)
        tests_root = run_root / "input-tests"
        output_root = run_root / "output"
        selected = _copy_test_inputs(
            test_paths,
            project_tests,
            tests_root,
            repeats=repeat_tests,
        )
        spec = SandboxSpec(
            project_id=target.project,
            archive_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            requested_python=environment.requested_python,
            detected_python=manifest.image.python_minor,
            source_directory=environment.source_directory,
            test_directory=".",
            dependency_policy=DependencyPolicy(DependencyMode.NONE),
            runner_profile=RunnerProfile(environment.runner_profile),
            coverage_mode=CoverageMode.STATEMENT_AND_BRANCH,
            allowed_environment_variables=("LANG", "LC_ALL", "PYTHONHASHSEED", "TZ"),
            resource_limits=ResourceLimits(),
        )
        run_spec = RunSpec(
            run_id=(
                run_id
                if len(run_id) <= 100
                else f"{run_id[:83]}-{hashlib.sha256(run_id.encode()).hexdigest()[:16]}"
            ),
            kind=kind,
            environment_fingerprint=manifest.fingerprint,
            test_paths=tuple(selected),
            source_file=target.source_file,
            symbol=target.symbol,
        )
        result = self.executor.execute(
            DockerExecutionRequest(
                image_digest=environment.image_digest,
                artifact_archive=environment.artifact_archive,
                artifact_manifest=environment.artifact_manifest,
                source_root=environment.source_root,
                tests_root=tests_root,
                output_root=output_root,
                sandbox_spec=spec,
                run_spec=run_spec,
                environment={"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PYTHONHASHSEED": "0", "TZ": "UTC"},
            )
        )
        require_matching_fingerprint(run_spec, result)
        coverage = None
        if result.coverage_artifact:
            coverage = _normalized_symbol_coverage(
                output_root / result.coverage_artifact,
                environment=environment,
                target=target,
                result=result,
            )
        return SandboxEvaluation(result=result, coverage=coverage)
