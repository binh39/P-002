from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .coveragepy import SymbolCoverage, load_report, run_coverage, symbol_coverage
from .metrics import build_feedback, score_symbol
from .models import BatchRunRecord, BatchTargetResult, ExperimentConfig, RunRecord, SymbolTarget
from .subprocesses import run_streamed


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
    environment["PYTHONPATH"] = (
        os.pathsep.join(roots) + os.pathsep + environment.get("PYTHONPATH", "")
    )
    environment["MPLBACKEND"] = "Agg"
    # Generated tests may iterate over sets or otherwise depend on Python's
    # randomized hash order. CoverUp validates a test in one subprocess and the
    # runner measures the saved suite in another; without a fixed seed, a test
    # can pass generation and fail final coverage with different input ordering.
    environment["PYTHONHASHSEED"] = "0"
    return environment


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
    traces: list[dict], target: SymbolTarget, *, workspace: Path,
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
        traces, target, workspace=source_workspace,
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

    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config

    def evaluate(
        self,
        target: SymbolTarget,
        prompt_template: Path,
        *,
        candidate_id: str | None = None,
    ) -> RunRecord:
        """Compatibility wrapper for evaluating a single target as a one-item batch."""
        batch = self.evaluate_batch(
            [target], prompt_template, candidate_id=candidate_id, split=target.split
        )
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
        if not targets:
            raise ValueError("evaluate_batch requires at least one target")
        target_splits = {target.split for target in targets}
        if split is None:
            if len(target_splits) != 1:
                raise ValueError(f"Batch targets must share one split, got {sorted(target_splits)}")
            split = next(iter(target_splits))
        elif target_splits != {split}:
            raise ValueError(
                f"Batch targets do not match requested split {split!r}: {sorted(target_splits)}"
            )
        safe_split = re.sub(r"[^A-Za-z0-9_.-]+", "_", split).strip("._-")
        if not safe_split:
            raise ValueError("split must contain at least one safe path character")
        projects = sorted({target.project for target in targets})
        project_label = projects[0] if len(projects) == 1 else "multi-project"
        run_id = f"{project_label}-{safe_split}-batch-{uuid.uuid4().hex[:8]}"
        if candidate_id is None:
            candidate_id = hashlib.sha256(prompt_template.resolve().read_bytes()).hexdigest()[:16]
        safe_candidate_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", candidate_id).strip("._-")
        if not safe_candidate_id:
            raise ValueError("candidate_id must contain at least one safe path character")
        workspace_prefixes = {
            "candidate": "tests_candidate",
            "baseline": "tests_base_line",
        }
        if workspace_kind not in workspace_prefixes:
            raise ValueError(f"Unsupported workspace kind: {workspace_kind!r}")
        generated_tests_root = (
            self.config.artifacts_dir.resolve() / "generated_tests" / safe_split
        )
        work_tests = (
            generated_tests_root
            / f"{workspace_prefixes[workspace_kind]}_{safe_candidate_id}"
        )
        if work_tests.exists():
            if any(work_tests.iterdir()):
                raise RuntimeError(
                    "Incomplete non-empty candidate workspace exists without a usable "
                    f"batch cache: {work_tests}. Use a fresh artifacts directory and "
                    "workspace, or archive the incomplete workspace before retrying."
                )
            work_tests.rmdir()
        work_tests.mkdir(parents=True)

        run_dir = (
            self.config.artifacts_dir.resolve()
            / "runs"
            / safe_candidate_id
            / safe_split
            / run_id
        )
        run_dir.mkdir(parents=True, exist_ok=False)

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
        package_dirs = {
            project: self.config.package_dir_for(project).resolve()
            for project in projects
        }
        missing_packages = [str(path) for path in package_dirs.values() if not path.is_dir()]
        if missing_packages:
            raise FileNotFoundError(
                "Package directory does not exist for a target project: "
                + ", ".join(missing_packages)
            )
        environment = _test_environment(
            self.config.project_root,
            tuple(sorted({package_dir.parent for package_dir in package_dirs.values()})),
        )

        final_workspaces: dict[str, Path] = {}
        for project in projects:
            workspace = work_tests if not multi_project else work_tests / project
            if multi_project:
                workspace.mkdir(parents=True, exist_ok=False)
            final_workspaces[project] = workspace.resolve()

        temporary_root = run_dir / "target_workspaces"
        pytest_temp_root = run_dir / "pytest_tmp"
        temporary_root.mkdir(parents=True, exist_ok=False)
        pytest_temp_root.mkdir(parents=True, exist_ok=False)
        jobs: list[_TargetEvaluationJob] = []
        for index, target in enumerate(targets):
            # Including the input position makes all paths collision-free even if
            # a malformed dataset contains the same target more than once.
            artifact_token = f"{_target_artifact_token(target)}_{index:04d}"
            temporary_workspace = temporary_root / artifact_token
            temporary_workspace.mkdir(parents=True, exist_ok=False)
            target_spec = run_dir / f"target_spec_{artifact_token}.json"
            target_spec.write_text(
                json.dumps(
                    [{"source_file": target.source_file, "symbol": target.symbol}],
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            coverup_log = run_dir / f"coverup_{artifact_token}.log"
            target_trace = run_dir / f"attempt_trace_{artifact_token}.jsonl"
            command = [
                sys.executable, "-u", "-m", "coverup",
                "--package-dir", str(package_dirs[target.project]),
                "--tests-dir", str(temporary_workspace),
                "--target-symbols", target.symbol,
                "--target-spec-file", str(target_spec),
                "--prompt", "gpt-v2",
                "--prompt-template-file", str(prompt_copy),
                "--model", self.config.coverup_model,
                "--max-attempts", str(self.config.max_attempts),
                "--prefix", "opt",
                "--log-file", str(coverup_log),
                "--trace-file", str(target_trace),
                "--target-context-max-chars", str(self.config.target_context_max_chars),
                "--no-checkpoint",
                # Target-specific coverage below is authoritative. Avoid CoverUp's
                # redundant final suite pass, especially expensive with repeats.
                "--no-final-coverage",
            ]
            if not self.config.target_context:
                command.append("--no-target-context")
            else:
                command.append("--target-context")
                if self.config.repository_test_context:
                    context_tests_dir = self.config.tests_dir_for(target.project).resolve()
                    if context_tests_dir.is_dir():
                        command.extend(["--context-tests-dir", str(context_tests_dir)])
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
            jobs.append(_TargetEvaluationJob(
                target=target,
                package_dir=package_dirs[target.project],
                final_workspace=final_workspaces[target.project],
                temporary_workspace=temporary_workspace,
                target_spec=target_spec,
                coverup_log=coverup_log,
                attempt_trace=target_trace,
                command=command,
                artifact_token=artifact_token,
            ))

        def evaluate_target(job: _TargetEvaluationJob) -> _TargetEvaluationOutcome:
            completed = run_streamed(
                job.command,
                cwd=self.config.project_root.resolve(),
                env=environment,
                label=f"CoverUp {job.target.source_file}::{job.target.symbol}",
                echo=False,
            )
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
                rewritten_traces, job.target, workspace=job.final_workspace,
            )
            target_discovery_failed = any(
                trace.get("outcome") == "target_discovery_failed"
                for trace in target_traces
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
                env=environment,
            )
            if after.returncode:
                feedback = (
                    "Score: 0. The generated tests for this target failed under "
                    "coverage.py:\n"
                    f"{after.stdout[-4000:]}"
                )
                report = load_report(after_json) if after_json.is_file() else None
                score_data = None
                if report is not None:
                    try:
                        measured_cov = symbol_coverage(
                            report, job.target.source_file, job.target.symbol
                        )
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
                    after_cov = symbol_coverage(
                        report, job.target.source_file, job.target.symbol
                    )
                except KeyError as exc:
                    target_result = BatchTargetResult(
                        target=job.target,
                        feedback=f"Score: 0. Coverage lookup failed: {exc}",
                        attempt_traces=target_traces,
                    )
                else:
                    metric_result = score_symbol(
                        _zero_coverage_like(after_cov), after_cov
                    )
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
            if target_discovery_failed:
                if target_result.score is None:
                    target_result.score = {}
                target_result.score["valid"] = False
                target_result.score["generator_exit_code"] = completed.returncode
                target_result.feedback = (
                    "Score: 0. Target discovery failed: CoverUp produced no "
                    "attempt trace or generated test for exact target "
                    f"{job.target.source_file}::{job.target.symbol}."
                )
            coverup_log_text = (
                job.coverup_log.read_text(encoding="utf-8")
                if job.coverup_log.is_file()
                else ""
            )
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
        worker_count = (
            1
            if self.config.rate_limit is not None
            else min(len(jobs), max(1, self.config.max_concurrency))
        )
        if worker_count == 1:
            outcomes = [evaluate_target(job) for job in jobs]
        else:
            with ThreadPoolExecutor(
                max_workers=worker_count,
                thread_name_prefix="target-evaluation",
            ) as executor:
                # map preserves caller order while each complete target lifecycle
                # (generation, consolidation and coverage) runs independently.
                outcomes = list(executor.map(evaluate_target, jobs))

        results = [outcome.target_result for outcome in outcomes]
        after_jsons = [outcome.coverage_after for outcome in outcomes]
        merged_attempt_traces = [
            trace for outcome in outcomes for trace in outcome.attempt_traces
        ]
        project_root_resolved = self.config.project_root.resolve()
        generated_tests = [
            _display_path(path, project_root_resolved)
            for outcome in outcomes
            for path in outcome.generated_tests
        ]
        final_exit_code = next(
            (
                outcome.generator_exit_code
                for outcome in outcomes
                if outcome.generator_exit_code
            ),
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
            coverage_after=(
                str(after_jsons[0].relative_to(run_dir)) if after_jsons else None
            ),
            stdout_file=str(stdout_file.relative_to(run_dir)),
            coverup_log_file=str(merged_coverup_log.relative_to(run_dir)),
            attempt_trace_file=(
                str(attempt_trace.relative_to(run_dir)) if attempt_trace.exists() else ""
            ),
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
        run_dir = (
            self.config.artifacts_dir.resolve()
            / "runs"
            / "baseline-existing"
            / safe_split
            / run_id
        )
        run_dir.mkdir(parents=True, exist_ok=False)
        grouped: dict[str, list[SymbolTarget]] = {}
        for target in targets:
            grouped.setdefault(target.project, []).append(target)
        projects = sorted(grouped)
        package_dirs = {
            project: self.config.package_dir_for(project).resolve()
            for project in projects
        }
        environment = _test_environment(
            self.config.project_root,
            tuple(sorted({path.parent for path in package_dirs.values()})),
        )
        multi_project = len(projects) > 1
        if multi_project:
            per_project_tests = {
                project: (tests_dir / project).resolve()
                for project in projects
            }
            missing_tests = [
                str(path) for path in per_project_tests.values() if not path.is_dir()
            ]
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
            package_dir = package_dirs[project]
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
                    results.append(BatchTargetResult(
                        target=target,
                        feedback=f"Score: 0. Coverage lookup failed: {exc}",
                    ))
                    continue
                metric_result = score_symbol(_zero_coverage_like(after_cov), after_cov)
                score_data = metric_result.as_dict()
                score_data["valid"] = True
                score_data["generator_exit_code"] = 0
                results.append(BatchTargetResult(
                    target=target,
                    score=score_data,
                    feedback=build_feedback(metric_result),
                ))
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
            generated_tests=[
                str(path) for path in sorted(tests_dir.rglob("test_*.py"))
            ],
            tests_workspace=str(tests_dir),
            coverage_after=(
                str(after_jsons[0].relative_to(run_dir)) if after_jsons else None
            ),
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
