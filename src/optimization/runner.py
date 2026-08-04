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
        source_tests = self.config.tests_dir.resolve()
        workspace_root = (
            self.config.workspace_root.resolve()
            if self.config.workspace_root is not None
            else source_tests.parent
        )
        workspace_root.mkdir(parents=True, exist_ok=True)
        work_tests = (
            workspace_root
            / f"{workspace_prefixes[workspace_kind]}_{safe_candidate_id}_{safe_split}"
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

        after_json = run_dir / "coverage_after.json"
        stdout_file = run_dir / "coverup.stdout.log"
        coverup_log = run_dir / "coverup.log"
        prompt_copy = run_dir / "prompt.json"
        shutil.copy2(prompt_template.resolve(), prompt_copy)

        environment = os.environ.copy()
        src_dir = self.config.project_root.resolve() / "src"
        environment["PYTHONPATH"] = str(src_dir) + os.pathsep + environment.get("PYTHONPATH", "")

        symbols = list(dict.fromkeys(target.symbol for target in targets))

        command = [
            sys.executable, "-m", "coverup",
            "--package-dir", str(self.config.package_dir.resolve()),
            "--tests-dir", str(work_tests),
            "--target-symbols", ",".join(symbols),
            "--prompt", "gpt-v2",
            "--prompt-template-file", str(prompt_copy),
            "--model", self.config.coverup_model,
            "--max-attempts", str(self.config.max_attempts),
            "--prefix", "opt",
            "--log-file", str(coverup_log),
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

        before_tests = {path.name for path in work_tests.glob("test_opt_*.py")}
        started_at = _now()
        started = time.monotonic()
        completed = subprocess.run(
            command,
            cwd=self.config.project_root.resolve(),
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        elapsed = time.monotonic() - started
        stdout_file.write_text(completed.stdout, encoding="utf-8")
        after_tests = sorted(
            str(path.relative_to(self.config.project_root.resolve()))
            for path in work_tests.glob("test_opt_*.py")
            if path.name not in before_tests
        )

        results: list[BatchTargetResult] = []
        after = run_coverage(
            project_root=self.config.project_root.resolve(),
            package_dir=self.config.package_dir.resolve(),
            tests_dir=work_tests,
            output=after_json,
            pytest_args=self.config.pytest_args,
            env=environment,
        )
        if after.returncode:
            feedback = (
                "Score: 0. The generated test suite failed under coverage.py:\n"
                f"{after.stdout[-4000:]}"
            )
            results = [BatchTargetResult(target=target, feedback=feedback) for target in targets]
        else:
            report = load_report(after_json)
            for target in targets:
                try:
                    after_cov = symbol_coverage(report, target.source_file, target.symbol)
                except KeyError as exc:
                    results.append(BatchTargetResult(
                        target=target,
                        feedback=f"Score: 0. Coverage lookup failed: {exc}",
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
                ))

        record = BatchRunRecord(
            run_id=run_id,
            split=split,
            targets=targets,
            command=command,
            started_at=started_at,
            finished_at=_now(),
            exit_code=completed.returncode,
            elapsed_seconds=elapsed,
            results=results,
            generated_tests=after_tests,
            tests_workspace=str(work_tests),
            coverage_after=str(after_json.relative_to(run_dir)) if after_json.exists() else None,
            stdout_file=str(stdout_file.relative_to(run_dir)),
            coverup_log_file=str(coverup_log.relative_to(run_dir)),
        )
        (run_dir / "record.json").write_text(
            json.dumps(record.as_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
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
        after_json = run_dir / "coverage_after.json"
        environment = os.environ.copy()
        src_dir = self.config.project_root.resolve() / "src"
        environment["PYTHONPATH"] = (
            str(src_dir) + os.pathsep + environment.get("PYTHONPATH", "")
        )
        started_at = _now()
        started = time.monotonic()
        completed = run_coverage(
            project_root=self.config.project_root.resolve(),
            package_dir=self.config.package_dir.resolve(),
            tests_dir=tests_dir,
            output=after_json,
            pytest_args=self.config.pytest_args,
            env=environment,
        )
        elapsed = time.monotonic() - started
        if completed.returncode:
            raise RuntimeError(
                "Existing baseline test suite failed under coverage.py:\n"
                f"{completed.stdout}"
            )
        report = load_report(after_json)
        results: list[BatchTargetResult] = []
        for target in targets:
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
        record = BatchRunRecord(
            run_id=run_id,
            split=split,
            targets=targets,
            command=["coverage.py", "pytest", str(tests_dir)],
            started_at=started_at,
            finished_at=_now(),
            exit_code=completed.returncode,
            elapsed_seconds=elapsed,
            results=results,
            generated_tests=[
                str(path) for path in sorted(tests_dir.rglob("test_*.py"))
            ],
            tests_workspace=str(tests_dir),
            coverage_after=str(after_json.relative_to(run_dir)),
        )
        (run_dir / "record.json").write_text(
            json.dumps(record.as_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return record


def build_feedback_placeholder(exit_code: int, stdout: str) -> str:
    if exit_code:
        return f"Score: 0. CoverUp exited with code {exit_code}:\n{stdout[-4000:]}"
    return "Score pending coverage.py evaluation."
