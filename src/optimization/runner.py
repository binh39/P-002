from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import sys
import time
import uuid
from concurrent.futures import CancelledError, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from src.promptopt_pause import ModelRateLimitPauseError, read_pause_request

from .coveragepy import SymbolCoverage, load_report, run_coverage, symbol_coverage
from .metrics import build_feedback, score_symbol
from .models import (
    BatchRunRecord,
    BatchTargetResult,
    EvaluationBackend,
    ExperimentConfig,
    RunRecord,
    SymbolTarget,
)
from .subprocesses import run_streamed

TARGET_EVALUATION_TIMEOUT_SECONDS = 20 * 60


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _display_path(path: Path, project_root: Path) -> str:
    """Return a path relative to the project root when possible, else absolute.

    Artifacts can live outside the project root (e.g. a GCS volume mount in
    Cloud Run), where relative_to() would raise ValueError.
    """
    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return str(path.resolve())


def _test_environment(
    project_root: Path,
    extra_roots: tuple[Path, ...] = (),
) -> dict[str, str]:
    """Build the subprocess environment used for every test evaluation.

    The Windows Store Python used by this workspace ships a broken Tcl/Tk, so
    matplotlib's default TkAgg backend fails whenever a generated test creates
    a figure (e.g. mlxtend plotting targets).  Forcing the headless Agg backend
    keeps figure creation fully functional without a GUI session.

    extra_roots: package parent directories (e.g. src/sample_repo/isort) added
    to PYTHONPATH so generated tests can import the sample repos by name
    (e.g. "from isort.core import process") without relying on pip-installed
    copies that may be missing or have a different API.
    """

    environment = os.environ.copy()
    src_dir = project_root.resolve() / "src"
    roots = [str(src_dir), *(str(root.resolve()) for root in extra_roots)]
    environment["PYTHONPATH"] = os.pathsep.join(roots) + os.pathsep + environment.get("PYTHONPATH", "")
    environment["MPLBACKEND"] = "Agg"
    # Generated tests may iterate over sets or otherwise depend on Python's
    # randomized hash order. CoverUp validates a test in one subprocess and the
    # runner measures the saved suite in another; without a fixed seed, a test
    # can pass generation and fail final coverage with different input ordering.
    environment["PYTHONHASHSEED"] = "0"
    return environment


def _configure_runtime_environment(environment: dict[str, str], runtime_python: Path | None) -> None:
    """Route every project subprocess through its restored virtualenv."""
    if runtime_python is None:
        return
    executable = runtime_python.resolve()
    environment["TESTGEN_PYTHON"] = str(executable)
    environment["VIRTUAL_ENV"] = str(executable.parent.parent)
    environment["PATH"] = os.pathsep.join([str(executable.parent), environment.get("PATH", "")])


def _zero_coverage_like(coverage: SymbolCoverage) -> SymbolCoverage:
    """Build the zero-coverage starting point for a from-scratch candidate."""
    return SymbolCoverage(
        source_file=coverage.source_file,
        symbol=coverage.symbol,
        covered_statements=0,
        num_statements=coverage.num_statements,
        covered_branches=0,
        num_branches=coverage.num_branches,
        executed_lines=(),
        missing_lines=tuple(sorted((*coverage.executed_lines, *coverage.missing_lines))),
        executed_branches=(),
        missing_branches=tuple(sorted((*coverage.executed_branches, *coverage.missing_branches))),
    )


def _load_attempt_traces(path: Path) -> list[dict]:
    """Load CoverUp's append-only trace, tolerating one incomplete final line."""
    if not path.is_file():
        return []
    traces = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            traces.append(value)
    return traces


def _traces_for_target(traces: list[dict], target: SymbolTarget) -> list[dict]:
    wanted_file = target.source_file.replace("\\", "/").lower()
    result = []
    for trace in traces:
        source_file = str(trace.get("source_file", "")).replace("\\", "/").lower()
        symbols = {str(trace.get("symbol", "")), str(trace.get("name", ""))}
        same_file = source_file.endswith(wanted_file) or wanted_file.endswith(source_file)
        if source_file and same_file and target.symbol in symbols:
            result.append(trace)
    return result


def _saved_tests_for_target(
    traces: list[dict],
    target: SymbolTarget,
    *,
    workspace: Path,
) -> list[Path]:
    """Return only saved test modules attributed to one exact target."""
    workspace = workspace.resolve()
    result: list[Path] = []
    seen: set[Path] = set()
    for trace in _traces_for_target(traces, target):
        saved_test = trace.get("saved_test")
        if not saved_test:
            continue
        path = Path(str(saved_test))
        if not path.is_absolute():
            path = workspace / path
        path = path.resolve()
        if path != workspace and workspace not in path.parents:
            continue
        if path.is_file() and path not in seen:
            seen.add(path)
            result.append(path)
    return result


def _target_artifact_token(target: SymbolTarget) -> str:
    identity = json.dumps(
        [target.project, target.source_file, target.symbol, target.split],
        ensure_ascii=True,
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]


def _package_dir_for_target(package_dir: Path, target: SymbolTarget) -> Path:
    """Return a CoverUp-compatible source directory for one target.

    CoverUp requires ``--package-dir`` to contain Python files directly.  An
    uploaded project commonly exposes a repository-level ``src`` directory,
    while the actual package (and the target source file) lives one or more
    levels below it.  Narrowing the directory to the target package preserves
    the uploaded layout and avoids an argparse failure before the model is
    called.  The import root remains the project layout's original root, so
    sibling imports continue to work.
    """
    package_dir = package_dir.resolve()
    if list(package_dir.glob("*.py")):
        return package_dir

    wanted = target.source_file.replace("\\", "/").lower().lstrip("./")
    if not wanted:
        return package_dir

    candidates: list[Path] = []
    for source in package_dir.rglob("*.py"):
        normalized = source.as_posix().lower()
        relative = source.relative_to(package_dir).as_posix().lower()
        if normalized.endswith("/" + wanted) or relative == wanted or relative.endswith("/" + wanted):
            candidates.append(source.parent.resolve())
    if not candidates:
        return package_dir
    return min(candidates, key=lambda path: (len(path.parts), path.as_posix()))


def _target_spec_source_file(package_dir: Path, target: SymbolTarget) -> str:
    """Normalize a target spec to the source base used by CoverUp.

    When ``package_dir`` is narrowed to a nested package, CoverUp compares
    target specs relative to that package's parent.  Uploaded manifests keep
    repository-relative paths (for example ``src/pkg/module.py``), so remove
    the path prefix before the selected package name.
    """
    normalized = target.source_file.replace("\\", "/").lower().lstrip("./")
    parts = normalized.split("/")
    package_name = package_dir.resolve().name.lower()
    for index in range(len(parts) - 1, -1, -1):
        if parts[index] == package_name:
            return "/".join(parts[index:])
    return target.source_file.replace("\\", "/")


def _consolidate_saved_tests(
    traces: list[dict],
    target: SymbolTarget,
    *,
    source_workspace: Path,
    destination_workspace: Path,
    token: str,
) -> tuple[list[dict], list[Path]]:
    """Copy one target's saved tests into the persistent candidate workspace."""
    source_workspace = source_workspace.resolve()
    destination_workspace = destination_workspace.resolve()
    sources = _saved_tests_for_target(
        traces,
        target,
        workspace=source_workspace,
    )
    replacements: dict[Path, Path] = {}
    copied: list[Path] = []
    for index, source in enumerate(sources, start=1):
        destination = destination_workspace / f"test_opt_{token}_{index}.py"
        shutil.copyfile(source, destination)
        replacements[source.resolve()] = destination.resolve()
        copied.append(destination.resolve())

    rewritten = []
    for original in traces:
        trace = dict(original)
        saved_test = trace.get("saved_test")
        if saved_test:
            source = Path(str(saved_test))
            if not source.is_absolute():
                source = source_workspace / source
            replacement = replacements.get(source.resolve())
            if replacement is not None:
                trace["saved_test"] = str(replacement)
        rewritten.append(trace)
    return rewritten, copied


@dataclass(frozen=True)
class _TargetEvaluationJob:
    target: SymbolTarget
    package_dir: Path
    final_workspace: Path
    temporary_workspace: Path
    target_spec: Path
    coverup_log: Path
    attempt_trace: Path
    command: list[str]
    artifact_token: str
    environment: dict[str, str]


@dataclass
class _TargetEvaluationOutcome:
    target_result: BatchTargetResult
    command: list[str]
    generator_exit_code: int
    stdout: str
    coverup_log: str
    attempt_traces: list[dict]
    generated_tests: list[Path]
    coverage_after: Path


def _checkpoint_path(path: Path, artifacts_root: Path) -> str:
    return path.resolve().relative_to(artifacts_root.resolve()).as_posix()


def _portable_attempt_traces(traces: list[dict], artifacts_root: Path) -> list[dict]:
    portable = []
    for original in traces:
        trace = dict(original)
        saved_test = trace.get("saved_test")
        if saved_test:
            try:
                relative = _checkpoint_path(Path(str(saved_test)), artifacts_root)
            except ValueError:
                pass
            else:
                trace["saved_test"] = {"artifact_relative": relative}
        portable.append(trace)
    return portable


def _restored_attempt_traces(traces: list[dict], artifacts_root: Path) -> list[dict]:
    restored = []
    for original in traces:
        trace = dict(original)
        saved_test = trace.get("saved_test")
        if isinstance(saved_test, dict) and isinstance(saved_test.get("artifact_relative"), str):
            trace["saved_test"] = str((artifacts_root / saved_test["artifact_relative"]).resolve())
        restored.append(trace)
    return restored


def _save_target_checkpoint(
    path: Path,
    outcome: _TargetEvaluationOutcome,
    *,
    artifacts_root: Path,
) -> None:
    """Persist one completed target atomically so a paused batch can skip it."""
    target_result = outcome.target_result.as_dict()
    target_result["attempt_traces"] = _portable_attempt_traces(
        target_result.get("attempt_traces", []),
        artifacts_root,
    )
    payload = {
        "schema_version": 1,
        "target_result": target_result,
        "command": outcome.command,
        "generator_exit_code": outcome.generator_exit_code,
        "stdout": outcome.stdout,
        "coverup_log": outcome.coverup_log,
        "attempt_traces": _portable_attempt_traces(outcome.attempt_traces, artifacts_root),
        "generated_tests": [_checkpoint_path(path, artifacts_root) for path in outcome.generated_tests],
        "coverage_after": _checkpoint_path(outcome.coverage_after, artifacts_root),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, path)


def _load_target_checkpoint(path: Path, *, artifacts_root: Path) -> _TargetEvaluationOutcome:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise RuntimeError(f"Unsupported target checkpoint schema: {path}")
    result = payload["target_result"]
    target_result = BatchTargetResult(
        target=SymbolTarget(**result["target"]),
        score=result.get("score"),
        feedback=result.get("feedback", ""),
        attempt_traces=_restored_attempt_traces(result.get("attempt_traces", []), artifacts_root),
    )
    return _TargetEvaluationOutcome(
        target_result=target_result,
        command=list(payload["command"]),
        generator_exit_code=int(payload.get("generator_exit_code", 0)),
        stdout=str(payload.get("stdout", "")),
        coverup_log=str(payload.get("coverup_log", "")),
        attempt_traces=_restored_attempt_traces(payload.get("attempt_traces", []), artifacts_root),
        generated_tests=[(artifacts_root / item).resolve() for item in payload.get("generated_tests", [])],
        coverage_after=(artifacts_root / payload["coverage_after"]).resolve(),
    )


def _prune_run_dir(run_dir: Path) -> None:
    """Keep only record.json in a batch run directory after it is scored.

    GEPA evaluates hundreds of targets per candidate, and every evaluation
    writes a fresh run directory.  Keeping coverage reports (~0.5-2 MB each)
    and CoverUp logs would quickly fill the container's ephemeral disk on long
    runs.  Per-target scores, feedback and attempt traces are already persisted
    in the batch cache (and scores/feedback again in record.json), so nothing
    else in the run directory is read afterwards.
    """
    for stale in run_dir.iterdir():
        if stale.name == "record.json":
            continue
        if stale.is_dir():
            shutil.rmtree(stale)
        else:
            stale.unlink(missing_ok=True)


class CoverUpExperimentRunner:
    """Generate one prompt batch and score each symbol with only its traced tests."""

    def __init__(
        self,
        config: ExperimentConfig,
        *,
        evaluation_backend: EvaluationBackend | None = None,
    ) -> None:
        self.config = config
        self.evaluation_backend = evaluation_backend

    def evaluate(
        self,
        target: SymbolTarget,
        prompt_template: Path,
        *,
        candidate_id: str | None = None,
    ) -> RunRecord:
        """Compatibility wrapper for evaluating a single target as a one-item batch."""
        batch = self.evaluate_batch([target], prompt_template, candidate_id=candidate_id, split=target.split)
        result = batch.results[0]
        return RunRecord(
            run_id=batch.run_id,
            target=target,
            command=batch.command,
            started_at=batch.started_at,
            finished_at=batch.finished_at,
            exit_code=batch.exit_code,
            elapsed_seconds=batch.elapsed_seconds,
            generated_tests=batch.generated_tests,
            tests_workspace=batch.tests_workspace,
            coverage_before=None,
            coverage_after=batch.coverage_after,
            score=result.score,
            feedback=result.feedback,
            stdout_file=batch.stdout_file,
            coverup_log_file=batch.coverup_log_file,
            attempt_trace_file=batch.attempt_trace_file,
        )

    def evaluate_optimizer_test(
        self,
        target: SymbolTarget,
        test_module: str,
        *,
        experiment_id: str,
    ) -> dict:
        """Run one optimizer-authored diagnostic test without adding it to a candidate.

        These experiments are teacher evidence for reflection only.  They live
        under ``optimizer_experiments`` and are never copied into the generated
        candidate workspace, so GEPA still scores a prompt by asking CoverUp to
        generate a fresh test module from that prompt.
        """
        if self.evaluation_backend is not None:
            return self.evaluation_backend.evaluate_optimizer_test(
                target,
                test_module,
                experiment_id=experiment_id,
            )
        if not isinstance(test_module, str) or not test_module.strip():
            raise ValueError("Optimizer experiment requires a non-empty test module")
        if len(test_module.encode("utf-8")) > 64 * 1024:
            raise ValueError("Optimizer experiment test module exceeds 64 KiB")
        try:
            tree = ast.parse(test_module)
        except SyntaxError as exc:
            return {
                "experiment_id": experiment_id,
                "target": target.__dict__,
                "pytest_passed": False,
                "pytest_exit_code": None,
                "score": 0.0,
                "validation_error": f"Invalid Python test module: {exc}",
                "stdout": "",
            }
        has_test = any(
            isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith("test_")
            for node in ast.walk(tree)
        )
        if not has_test:
            return {
                "experiment_id": experiment_id,
                "target": target.__dict__,
                "pytest_passed": False,
                "pytest_exit_code": None,
                "score": 0.0,
                "validation_error": "The module defines no test_* function.",
                "stdout": "",
            }

        safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", experiment_id).strip("._-")
        if not safe_id:
            raise ValueError("experiment_id must contain a safe path character")
        run_dir = self.config.artifacts_dir.resolve() / "optimizer_experiments" / safe_id
        run_dir.mkdir(parents=True, exist_ok=False)
        test_path = run_dir / "test_optimizer_experiment.py"
        test_path.write_text(test_module, encoding="utf-8")
        coverage_path = run_dir / "coverage.json"
        package_dir = self.config.package_dir_for(target.project).resolve()
        environment = _test_environment(
            self.config.project_root,
            (self.config.import_root_for(target.project),),
        )
        _configure_runtime_environment(environment, self.config.python_for(target.project))
        completed = run_coverage(
            project_root=self.config.project_root.resolve(),
            package_dir=package_dir,
            tests_dir=run_dir,
            test_paths=[test_path],
            pytest_basetemp=run_dir / "pytest_tmp",
            output=coverage_path,
            pytest_args=self.config.pytest_args,
            repeat_tests=self.config.repeat_tests,
            env=environment,
        )
        result = {
            "experiment_id": experiment_id,
            "target": target.__dict__,
            "pytest_passed": completed.returncode == 0,
            "pytest_exit_code": completed.returncode,
            "score": 0.0,
            "stdout": (
                completed.stdout
                if os.environ.get("PROMPTOPT_FULL_REFLECTION_LOGS", "").strip().lower() in {"1", "true", "yes", "on"}
                else completed.stdout[-6000:]
            ),
            "test_file": str(test_path),
        }
        if coverage_path.is_file():
            try:
                measured = symbol_coverage(load_report(coverage_path), target.source_file, target.symbol)
            except KeyError as exc:
                result["coverage_error"] = str(exc)
            else:
                metric = score_symbol(_zero_coverage_like(measured), measured)
                result.update(
                    {
                        "score": metric.score if completed.returncode == 0 else 0.0,
                        "measured_score": metric.score,
                        "covered_statements": metric.covered_statements,
                        "num_statements": metric.num_statements,
                        "covered_branches": metric.covered_branches,
                        "num_branches": metric.num_branches,
                        "gained_lines": list(metric.gained_lines),
                        "gained_branches": [list(branch) for branch in metric.gained_branches],
                        "remaining_lines": list(metric.remaining_lines),
                        "remaining_branches": [list(branch) for branch in metric.remaining_branches],
                    }
                )
        (run_dir / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        coverage_path.unlink(missing_ok=True)
        coverage_path.with_suffix(".data").unlink(missing_ok=True)
        shutil.rmtree(run_dir / "pytest_tmp", ignore_errors=True)
        return result

    def evaluate_batch(
        self,
        targets: list[SymbolTarget],
        prompt_template: Path,
        *,
        candidate_id: str | None = None,
        split: str | None = None,
        workspace_kind: str = "candidate",
    ) -> BatchRunRecord:
        """Evaluate targets concurrently and retain one consolidated candidate suite."""
        if self.evaluation_backend is not None:
            return self.evaluation_backend.evaluate_batch(
                targets,
                prompt_template,
                candidate_id=candidate_id,
                split=split,
                workspace_kind=workspace_kind,
            )
        if not targets:
            raise ValueError("evaluate_batch requires at least one target")
        target_splits = {target.split for target in targets}
        if split is None:
            if len(target_splits) != 1:
                raise ValueError(f"Batch targets must share one split, got {sorted(target_splits)}")
            split = next(iter(target_splits))
        elif target_splits != {split}:
            raise ValueError(f"Batch targets do not match requested split {split!r}: {sorted(target_splits)}")
        safe_split = re.sub(r"[^A-Za-z0-9_.-]+", "_", split).strip("._-")
        if not safe_split:
            raise ValueError("split must contain at least one safe path character")
        projects = sorted({target.project for target in targets})
        project_label = projects[0] if len(projects) == 1 else "multi-project"
        if candidate_id is None:
            candidate_id = hashlib.sha256(prompt_template.resolve().read_bytes()).hexdigest()[:16]
        safe_candidate_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", candidate_id).strip("._-")
        if not safe_candidate_id:
            raise ValueError("candidate_id must contain at least one safe path character")
        run_id = f"{project_label}-{safe_split}-batch-{safe_candidate_id[:24]}"
        artifacts_root = self.config.artifacts_dir.resolve()
        run_dir = artifacts_root / "runs" / safe_candidate_id / safe_split / run_id
        partial_dir = run_dir / "target_checkpoints"
        has_target_checkpoints = partial_dir.is_dir() and any(partial_dir.glob("*.json"))
        workspace_prefixes = {
            "candidate": "tests_candidate",
            "baseline": "tests_base_line",
        }
        if workspace_kind not in workspace_prefixes:
            raise ValueError(f"Unsupported workspace kind: {workspace_kind!r}")
        generated_tests_root = self.config.artifacts_dir.resolve() / "generated_tests" / safe_split
        work_tests = generated_tests_root / f"{workspace_prefixes[workspace_kind]}_{safe_candidate_id}"
        if work_tests.exists():
            if any(work_tests.iterdir()):
                if has_target_checkpoints:
                    pass
                elif os.environ.get("PROMPTOPT_RESUMING") == "1":
                    shutil.rmtree(work_tests)
                else:
                    raise RuntimeError(
                        "Incomplete non-empty candidate workspace exists without a usable "
                        f"batch cache: {work_tests}. Use a fresh artifacts directory and "
                        "workspace, or archive the incomplete workspace before retrying."
                    )
            if work_tests.exists() and not any(work_tests.iterdir()):
                work_tests.rmdir()
        work_tests.mkdir(parents=True, exist_ok=has_target_checkpoints)
        if run_dir.exists() and not has_target_checkpoints:
            if os.environ.get("PROMPTOPT_RESUMING") == "1":
                shutil.rmtree(run_dir)
            else:
                raise RuntimeError(f"Incomplete batch run directory already exists: {run_dir}")
        run_dir.mkdir(parents=True, exist_ok=has_target_checkpoints)

        stdout_file = run_dir / "coverup.stdout.log"
        attempt_trace = run_dir / "attempt_trace.jsonl"
        prompt_copy = run_dir / "prompt.json"
        # Use copyfile() instead of copy()/copy2(): both of those copy file
        # metadata (utime/chmod), which Cloud Run's GCS volume mount (gcsfuse)
        # does not support and fails with PermissionError. Content only.
        shutil.copyfile(prompt_template.resolve(), prompt_copy)

        grouped: dict[str, list[SymbolTarget]] = {}
        for target in targets:
            grouped.setdefault(target.project, []).append(target)
        projects = sorted(grouped)
        multi_project = len(projects) > 1
        package_dirs = {project: self.config.package_dir_for(project).resolve() for project in projects}
        missing_packages = [str(path) for path in package_dirs.values() if not path.is_dir()]
        if missing_packages:
            raise FileNotFoundError(
                "Package directory does not exist for a target project: " + ", ".join(missing_packages)
            )
        environments: dict[str, dict[str, str]] = {}
        for project in projects:
            environment = _test_environment(
                self.config.project_root,
                (self.config.import_root_for(project),),
            )
            _configure_runtime_environment(environment, self.config.python_for(project))
            environments[project] = environment

        final_workspaces: dict[str, Path] = {}
        for project in projects:
            workspace = work_tests if not multi_project else work_tests / project
            if multi_project:
                # A resumed multi-project batch restores these project
                # directories together with its durable target checkpoints.
                # Preserve completed targets' consolidated tests and allow
                # unfinished targets to continue in the same workspace.
                workspace.mkdir(parents=True, exist_ok=has_target_checkpoints)
            final_workspaces[project] = workspace.resolve()

        temporary_root = run_dir / "target_workspaces"
        pytest_temp_root = run_dir / "pytest_tmp"
        shutil.rmtree(temporary_root, ignore_errors=True)
        shutil.rmtree(pytest_temp_root, ignore_errors=True)
        temporary_root.mkdir(parents=True, exist_ok=False)
        pytest_temp_root.mkdir(parents=True, exist_ok=False)
        jobs: list[_TargetEvaluationJob] = []
        restored_outcomes: dict[int, _TargetEvaluationOutcome] = {}
        for index, target in enumerate(targets):
            # Including the input position makes all paths collision-free even if
            # a malformed dataset contains the same target more than once.
            artifact_token = f"{_target_artifact_token(target)}_{index:04d}"
            checkpoint = partial_dir / f"{artifact_token}.json"
            if checkpoint.is_file():
                restored = _load_target_checkpoint(checkpoint, artifacts_root=artifacts_root)
                if restored.target_result.target != target:
                    raise RuntimeError(f"Target checkpoint identity mismatch: {checkpoint}")
                restored_outcomes[index] = restored
                continue
            temporary_workspace = temporary_root / artifact_token
            temporary_workspace.mkdir(parents=True, exist_ok=False)
            target_package_dir = _package_dir_for_target(package_dirs[target.project], target)
            target_spec = run_dir / f"target_spec_{artifact_token}.json"
            target_spec.write_text(
                json.dumps(
                    [
                        {
                            "source_file": _target_spec_source_file(target_package_dir, target),
                            "symbol": target.symbol,
                        }
                    ],
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            coverup_log = run_dir / f"coverup_{artifact_token}.log"
            target_trace = run_dir / f"attempt_trace_{artifact_token}.jsonl"
            command = [
                sys.executable,
                "-u",
                "-m",
                "coverup",
                "--package-dir",
                str(target_package_dir),
                "--tests-dir",
                str(temporary_workspace),
                "--target-symbols",
                target.symbol,
                "--target-spec-file",
                str(target_spec),
                "--prompt",
                "gpt-v2",
                "--prompt-template-file",
                str(prompt_copy),
                "--model",
                self.config.coverup_model,
                "--max-attempts",
                str(self.config.max_attempts),
                "--prefix",
                "opt",
                "--log-file",
                str(coverup_log),
                "--trace-file",
                str(target_trace),
                "--no-checkpoint",
                # Target-specific coverage below is authoritative. Avoid CoverUp's
                # redundant final suite pass, especially expensive with repeats.
                "--no-final-coverage",
            ]
            if self.config.repeat_tests:
                command.extend(["--repeat-tests", str(self.config.repeat_tests)])
            else:
                command.append("--no-repeat-tests")
            if self.config.pytest_args:
                command.extend(["--pytest-args", self.config.pytest_args])
            # Global parallelism is owned by the outer pool. Keeping a child at
            # one prevents max_concurrency squared processes and API requests.
            command.extend(["--max-concurrency", "1"])
            if self.config.rate_limit is not None:
                command.extend(["--rate-limit", str(self.config.rate_limit)])
            jobs.append(
                _TargetEvaluationJob(
                    target=target,
                    package_dir=target_package_dir,
                    final_workspace=final_workspaces[target.project],
                    temporary_workspace=temporary_workspace,
                    target_spec=target_spec,
                    coverup_log=coverup_log,
                    attempt_trace=target_trace,
                    command=command,
                    artifact_token=artifact_token,
                    environment=environments[target.project],
                )
            )

        def evaluate_target(job: _TargetEvaluationJob) -> _TargetEvaluationOutcome:
            # Run CoverUp from the target project's import root.  Uploaded
            # projects are staged outside /app, while CoverUp measures the
            # initial suite with ``--source`` and each generated test without
            # it.  Keeping the working directory at the import root makes
            # Python import the staged checkout and gives SlipCover one stable
            # path basis for both measurements.  Running every project from
            # /app can otherwise import an installed copy of the same package
            # or report a different relative filename, turning a valid test
            # into a false zero-coverage result.
            coverup_cwd = self.config.import_root_for(job.target.project).resolve()
            completed = run_streamed(
                job.command,
                cwd=coverup_cwd,
                env=job.environment,
                label=f"CoverUp {job.target.source_file}::{job.target.symbol}",
                echo=False,
                announce=True,
                timeout=TARGET_EVALUATION_TIMEOUT_SECONDS,
                echo_prefixes=("PROMPTOPT_MODEL_ERROR ",),
            )
            if read_pause_request() is not None:
                raise ModelRateLimitPauseError("Model rate limit pause requested")
            raw_traces = _load_attempt_traces(job.attempt_trace)
            try:
                rewritten_traces, copied_tests = _consolidate_saved_tests(
                    raw_traces,
                    job.target,
                    source_workspace=job.temporary_workspace,
                    destination_workspace=job.final_workspace,
                    token=job.artifact_token,
                )
            finally:
                # Temporary per-target folders provide the old isolation and are
                # discarded as soon as their attributed tests have been retained.
                shutil.rmtree(job.temporary_workspace, ignore_errors=True)

            target_traces = _traces_for_target(rewritten_traces, job.target)
            selected_tests = _saved_tests_for_target(
                rewritten_traces,
                job.target,
                workspace=job.final_workspace,
            )
            if not selected_tests:
                empty_test = run_dir / f"empty_target_{job.artifact_token}.py"
                empty_test.write_text(
                    "# No generated test was saved for this target.\n",
                    encoding="utf-8",
                )
                selected_tests = [empty_test]
            after_json = run_dir / f"coverage_after_{job.artifact_token}.json"
            after = run_coverage(
                project_root=self.config.project_root.resolve(),
                package_dir=job.package_dir,
                tests_dir=job.final_workspace,
                test_paths=selected_tests,
                pytest_basetemp=pytest_temp_root / job.artifact_token,
                output=after_json,
                pytest_args=self.config.pytest_args,
                repeat_tests=self.config.repeat_tests,
                env=job.environment,
            )
            if after.returncode:
                feedback = (
                    f"Score: 0. The generated tests for this target failed under coverage.py:\n{after.stdout[-4000:]}"
                )
                report = load_report(after_json) if after_json.is_file() else None
                score_data = None
                if report is not None:
                    try:
                        measured_cov = symbol_coverage(report, job.target.source_file, job.target.symbol)
                    except KeyError:
                        pass
                    else:
                        zero_cov = _zero_coverage_like(measured_cov)
                        score_data = score_symbol(zero_cov, zero_cov).as_dict()
                        score_data["valid"] = True
                        score_data["tests_passed"] = False
                        score_data["pytest_exit_code"] = after.returncode
                        score_data["generator_exit_code"] = completed.returncode
                target_result = BatchTargetResult(
                    target=job.target,
                    score=score_data,
                    feedback=feedback,
                    attempt_traces=target_traces,
                )
            else:
                report = load_report(after_json)
                try:
                    after_cov = symbol_coverage(report, job.target.source_file, job.target.symbol)
                except KeyError as exc:
                    target_result = BatchTargetResult(
                        target=job.target,
                        feedback=f"Score: 0. Coverage lookup failed: {exc}",
                        attempt_traces=target_traces,
                    )
                else:
                    metric_result = score_symbol(_zero_coverage_like(after_cov), after_cov)
                    score_data = metric_result.as_dict()
                    score_data["valid"] = True
                    score_data["generator_exit_code"] = completed.returncode
                    target_result = BatchTargetResult(
                        target=job.target,
                        score=score_data,
                        feedback=build_feedback(
                            metric_result,
                            coverup_exit_code=completed.returncode,
                        ),
                        attempt_traces=target_traces,
                    )
            coverup_log_text = job.coverup_log.read_text(encoding="utf-8") if job.coverup_log.is_file() else ""
            return _TargetEvaluationOutcome(
                target_result=target_result,
                command=job.command,
                generator_exit_code=completed.returncode,
                stdout=completed.stdout,
                coverup_log=coverup_log_text,
                attempt_traces=rewritten_traces,
                generated_tests=copied_tests,
                coverage_after=after_json,
            )

        started_at = _now()
        started = time.monotonic()
        # A configured limiter is process-local, so multiple CoverUp processes
        # would exceed it. Preserve its semantics by serializing that rare mode.
        worker_count = 1 if self.config.rate_limit is not None else min(len(jobs), max(1, self.config.max_concurrency))
        outcomes_by_index = dict(restored_outcomes)
        job_positions = {job.artifact_token: int(job.artifact_token.rsplit("_", 1)[1]) for job in jobs}

        def retain_outcome(job: _TargetEvaluationJob, outcome: _TargetEvaluationOutcome) -> None:
            position = job_positions[job.artifact_token]
            _save_target_checkpoint(
                partial_dir / f"{job.artifact_token}.json",
                outcome,
                artifacts_root=artifacts_root,
            )
            outcomes_by_index[position] = outcome

        if worker_count == 1:
            for job in jobs:
                outcome = evaluate_target(job)
                retain_outcome(job, outcome)
        else:
            pause_error: ModelRateLimitPauseError | None = None
            first_error: BaseException | None = None
            with ThreadPoolExecutor(
                max_workers=worker_count,
                thread_name_prefix="target-evaluation",
            ) as executor:
                futures = {executor.submit(evaluate_target, job): job for job in jobs}
                for future in as_completed(futures):
                    job = futures[future]
                    try:
                        outcome = future.result()
                    except CancelledError:
                        continue
                    except ModelRateLimitPauseError as exc:
                        pause_error = pause_error or exc
                        for pending in futures:
                            pending.cancel()
                    except BaseException as exc:  # noqa: BLE001 - re-raise after retaining peers
                        first_error = first_error or exc
                        for pending in futures:
                            pending.cancel()
                    else:
                        retain_outcome(job, outcome)
            if pause_error is not None:
                raise pause_error
            if first_error is not None:
                raise first_error

        if len(outcomes_by_index) != len(targets):
            raise RuntimeError(f"Batch checkpoint is incomplete: {len(outcomes_by_index)}/{len(targets)} targets")
        outcomes = [outcomes_by_index[index] for index in range(len(targets))]

        results = [outcome.target_result for outcome in outcomes]
        after_jsons = [outcome.coverage_after for outcome in outcomes]
        merged_attempt_traces = [trace for outcome in outcomes for trace in outcome.attempt_traces]
        project_root_resolved = self.config.project_root.resolve()
        generated_tests = [
            _display_path(path, project_root_resolved) for outcome in outcomes for path in outcome.generated_tests
        ]
        final_exit_code = next(
            (outcome.generator_exit_code for outcome in outcomes if outcome.generator_exit_code),
            0,
        )
        elapsed = time.monotonic() - started
        stdout_file.write_text(
            "\n".join(
                f"=== {outcome.target_result.target.project}:"
                f"{outcome.target_result.target.symbol} ===\n{outcome.stdout}"
                for outcome in outcomes
            ),
            encoding="utf-8",
        )
        attempt_trace.write_text(
            "".join(json.dumps(trace) + "\n" for trace in merged_attempt_traces),
            encoding="utf-8",
        )
        merged_coverup_log = run_dir / "coverup.log"
        merged_coverup_log.write_text(
            "\n".join(
                f"=== {outcome.target_result.target.project}:"
                f"{outcome.target_result.target.symbol} ===\n{outcome.coverup_log}"
                for outcome in outcomes
            ),
            encoding="utf-8",
        )

        record = BatchRunRecord(
            run_id=run_id,
            split=split,
            targets=targets,
            command=outcomes[0].command,
            started_at=started_at,
            finished_at=_now(),
            exit_code=final_exit_code,
            elapsed_seconds=elapsed,
            results=results,
            generated_tests=generated_tests,
            tests_workspace=str(work_tests),
            coverage_after=(str(after_jsons[0].relative_to(run_dir)) if after_jsons else None),
            stdout_file=str(stdout_file.relative_to(run_dir)),
            coverup_log_file=str(merged_coverup_log.relative_to(run_dir)),
            attempt_trace_file=(str(attempt_trace.relative_to(run_dir)) if attempt_trace.exists() else ""),
        )
        (run_dir / "record.json").write_text(
            json.dumps(record.as_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        _prune_run_dir(run_dir)
        return record

    def evaluate_existing_tests_batch(
        self,
        targets: list[SymbolTarget],
        tests_dir: Path,
        *,
        split: str,
    ) -> BatchRunRecord:
        """Score an existing baseline suite without invoking CoverUp."""
        if not targets:
            raise ValueError("Baseline evaluation requires at least one target")
        if {target.split for target in targets} != {split}:
            raise ValueError(f"Baseline targets do not all belong to split {split!r}")
        tests_dir = tests_dir.resolve()
        if not tests_dir.is_dir():
            raise FileNotFoundError(f"Baseline tests directory does not exist: {tests_dir}")
        safe_split = re.sub(r"[^A-Za-z0-9_.-]+", "_", split).strip("._-")
        run_id = f"baseline-existing-{safe_split}-{uuid.uuid4().hex[:8]}"
        run_dir = self.config.artifacts_dir.resolve() / "runs" / "baseline-existing" / safe_split / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        grouped: dict[str, list[SymbolTarget]] = {}
        for target in targets:
            grouped.setdefault(target.project, []).append(target)
        projects = sorted(grouped)
        multi_project = len(projects) > 1
        if multi_project:
            per_project_tests = {project: (tests_dir / project).resolve() for project in projects}
            missing_tests = [str(path) for path in per_project_tests.values() if not path.is_dir()]
            if missing_tests:
                raise FileNotFoundError(
                    "Multi-project baseline evaluation requires one tests "
                    "subdirectory per project: " + ", ".join(missing_tests)
                )
        else:
            per_project_tests = {projects[0]: tests_dir}
        started_at = _now()
        started = time.monotonic()
        results: list[BatchTargetResult] = []
        after_jsons: list[Path] = []
        final_exit_code = 0
        for project in projects:
            group = grouped[project]
            environment = _test_environment(
                self.config.project_root,
                (self.config.import_root_for(project),),
            )
            _configure_runtime_environment(environment, self.config.python_for(project))
            package_dir = self.config.package_dir_for(project).resolve()
            safe_project = re.sub(r"[^A-Za-z0-9_.-]+", "_", project).strip("._-")
            suffix = "" if not multi_project else f"_{safe_project}"
            after_json = run_dir / f"coverage_after{suffix}.json"
            completed = run_coverage(
                project_root=self.config.project_root.resolve(),
                package_dir=package_dir,
                tests_dir=per_project_tests[project],
                output=after_json,
                pytest_args=self.config.pytest_args,
                repeat_tests=self.config.repeat_tests,
                env=environment,
            )
            final_exit_code = completed.returncode
            if completed.returncode:
                raise RuntimeError(
                    "Existing baseline test suite failed under coverage.py for "
                    f"project {project!r}:\n{completed.stdout}"
                )
            report = load_report(after_json)
            for target in group:
                try:
                    after_cov = symbol_coverage(report, target.source_file, target.symbol)
                except KeyError as exc:
                    results.append(
                        BatchTargetResult(
                            target=target,
                            feedback=f"Score: 0. Coverage lookup failed: {exc}",
                        )
                    )
                    continue
                metric_result = score_symbol(_zero_coverage_like(after_cov), after_cov)
                score_data = metric_result.as_dict()
                score_data["valid"] = True
                score_data["generator_exit_code"] = 0
                results.append(
                    BatchTargetResult(
                        target=target,
                        score=score_data,
                        feedback=build_feedback(metric_result),
                    )
                )
            after_jsons.append(after_json)
        elapsed = time.monotonic() - started
        record = BatchRunRecord(
            run_id=run_id,
            split=split,
            targets=targets,
            command=["coverage.py", "pytest", str(tests_dir)],
            started_at=started_at,
            finished_at=_now(),
            exit_code=final_exit_code,
            elapsed_seconds=elapsed,
            results=results,
            generated_tests=[str(path) for path in sorted(tests_dir.rglob("test_*.py"))],
            tests_workspace=str(tests_dir),
            coverage_after=(str(after_jsons[0].relative_to(run_dir)) if after_jsons else None),
        )
        (run_dir / "record.json").write_text(
            json.dumps(record.as_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        _prune_run_dir(run_dir)
        return record


def build_feedback_placeholder(exit_code: int, stdout: str) -> str:
    if exit_code:
        return f"Score: 0. CoverUp exited with code {exit_code}:\n{stdout[-4000:]}"
    return "Score pending coverage.py evaluation."
