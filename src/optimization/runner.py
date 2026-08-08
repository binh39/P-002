from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from .coveragepy import SymbolCoverage, load_report, run_coverage, symbol_coverage
from .metrics import build_feedback, score_symbol
from .models import BatchRunRecord, BatchTargetResult, ExperimentConfig, RunRecord, SymbolTarget


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
        if not stale.is_file():
            continue
        if stale.name == "record.json":
            continue
        stale.unlink(missing_ok=True)


class CoverUpExperimentRunner:
    """Evaluate one prompt on one symbol in an isolated copy of the test suite."""

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
        """Evaluate one prompt on many symbols with one CoverUp and coverage run."""
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

        stdout_parts: list[str] = []
        generated_tests: list[str] = []
        results: list[BatchTargetResult] = []
        merged_attempt_traces: list[dict] = []
        coverup_logs: list[Path] = []
        project_traces: list[Path] = []
        after_jsons: list[Path] = []
        final_exit_code = 0
        started_at = _now()
        started = time.monotonic()
        for project in projects:
            group = grouped[project]
            package_dir = package_dirs[project]
            workspace = work_tests if not multi_project else work_tests / project
            if multi_project:
                workspace.mkdir(parents=True, exist_ok=False)
            safe_project = re.sub(r"[^A-Za-z0-9_.-]+", "_", project).strip("._-")
            suffix = "" if not multi_project else f"_{safe_project}"
            coverup_log = run_dir / f"coverup{suffix}.log"
            project_trace = run_dir / f"attempt_trace{suffix}.jsonl"
            target_spec = run_dir / f"target_spec{suffix}.json"
            after_json = run_dir / f"coverage_after{suffix}.json"
            target_spec.write_text(
                json.dumps(
                    [
                        {
                            "source_file": target.source_file,
                            "symbol": target.symbol,
                        }
                        for target in group
                    ],
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            symbols = list(dict.fromkeys(target.symbol for target in group))
            command = [
                sys.executable, "-m", "coverup",
                "--package-dir", str(package_dir),
                "--tests-dir", str(workspace),
                "--target-symbols", ",".join(symbols),
                "--target-spec-file", str(target_spec),
                "--prompt", "gpt-v2",
                "--prompt-template-file", str(prompt_copy),
                "--model", self.config.coverup_model,
                "--max-attempts", str(self.config.max_attempts),
                "--prefix", "opt",
                "--log-file", str(coverup_log),
                "--trace-file", str(project_trace),
                "--no-checkpoint",
            ]
            if self.config.repeat_tests:
                command.extend(["--repeat-tests", str(self.config.repeat_tests)])
            else:
                command.append("--no-repeat-tests")
            if self.config.pytest_args:
                command.extend(["--pytest-args", self.config.pytest_args])
            command.extend(["--max-concurrency", str(self.config.max_concurrency)])
            if self.config.rate_limit is not None:
                command.extend(["--rate-limit", str(self.config.rate_limit)])

            before_tests = {path.name for path in workspace.glob("test_opt_*.py")}
            completed = subprocess.run(
                command,
                cwd=self.config.project_root.resolve(),
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            final_exit_code = completed.returncode
            stdout_parts.append(completed.stdout)
            project_root_resolved = self.config.project_root.resolve()
            generated_tests.extend(
                sorted(
                    _display_path(path, project_root_resolved)
                    for path in workspace.glob("test_opt_*.py")
                    if path.name not in before_tests
                )
            )
            attempt_traces = _load_attempt_traces(project_trace)
            merged_attempt_traces.extend(attempt_traces)

            after = run_coverage(
                project_root=self.config.project_root.resolve(),
                package_dir=package_dir,
                tests_dir=workspace,
                output=after_json,
                pytest_args=self.config.pytest_args,
                env=environment,
            )
            if after.returncode:
                feedback = (
                    "Score: 0. The generated test suite failed under coverage.py:\n"
                    f"{after.stdout[-4000:]}"
                )
                for target in group:
                    results.append(BatchTargetResult(
                        target=target,
                        feedback=feedback,
                        attempt_traces=_traces_for_target(attempt_traces, target),
                    ))
            else:
                report = load_report(after_json)
                for target in group:
                    try:
                        after_cov = symbol_coverage(report, target.source_file, target.symbol)
                    except KeyError as exc:
                        results.append(BatchTargetResult(
                            target=target,
                            feedback=f"Score: 0. Coverage lookup failed: {exc}",
                            attempt_traces=_traces_for_target(attempt_traces, target),
                        ))
                        continue
                    before_cov = _zero_coverage_like(after_cov)
                    metric_result = score_symbol(before_cov, after_cov)
                    score_data = metric_result.as_dict()
                    # The coverage run is the authority for test validity.  CoverUp may
                    # exit non-zero after some concurrent segments have already produced
                    # passing tests; invalidating the whole batch destroys useful signal.
                    score_data["valid"] = True
                    score_data["generator_exit_code"] = completed.returncode
                    results.append(BatchTargetResult(
                        target=target,
                        score=score_data,
                        feedback=build_feedback(
                            metric_result, coverup_exit_code=completed.returncode
                        ),
                        attempt_traces=_traces_for_target(attempt_traces, target),
                    ))
            coverup_logs.append(coverup_log)
            project_traces.append(project_trace)
            after_jsons.append(after_json)
        # Preserve the caller's target order in the merged results even though
        # per-project batches are executed in sorted project order.
        result_order = {id(target): index for index, target in enumerate(targets)}
        results.sort(key=lambda result: result_order[id(result.target)])
        elapsed = time.monotonic() - started
        stdout_file.write_text("\n".join(stdout_parts), encoding="utf-8")
        if multi_project:
            attempt_trace.write_text(
                "".join(json.dumps(trace) + "\n" for trace in merged_attempt_traces),
                encoding="utf-8",
            )

        record = BatchRunRecord(
            run_id=run_id,
            split=split,
            targets=targets,
            command=command,
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
            coverup_log_file=(
                str(coverup_logs[0].relative_to(run_dir)) if coverup_logs else ""
            ),
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
        environment = _test_environment(self.config.project_root)
        grouped: dict[str, list[SymbolTarget]] = {}
        for target in targets:
            grouped.setdefault(target.project, []).append(target)
        projects = sorted(grouped)
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
