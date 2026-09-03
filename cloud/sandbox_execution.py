"""Execute an allowlisted RunSpec and normalize coverage inside a sandbox."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tarfile
import time
from dataclasses import dataclass
from importlib.metadata import distributions
from pathlib import Path, PurePosixPath

from cloud.sandbox_builder import ArtifactManifest
from cloud.sandbox_contract import (
    CoverageMode,
    CoverageSummary,
    FailureStage,
    RunnerProfile,
    RunSpec,
    SandboxResult,
    SandboxSpec,
    SandboxStatus,
    TestCounts,
)
from cloud.sandbox_runner_profiles import RunnerDecision, select_runner_profile
from cloud.sandbox_security import bounded_redacted_text, redact_sensitive_text

NORMALIZED_COVERAGE_VERSION = 1


@dataclass(frozen=True, slots=True)
class ProcessOutcome:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bounded_text(path: Path, maximum: int) -> str:
    if not path.is_file() or maximum <= 0:
        return ""
    with path.open("rb") as stream:
        data = stream.read(maximum + 1)
    return bounded_redacted_text(data.decode("utf-8", errors="replace"), maximum)


def _network_denied_during_collection(output: str) -> bool:
    lowered = output.casefold()
    return any(
        marker in lowered
        for marker in (
            "network is unreachable",
            "temporary failure in name resolution",
            "name or service not known",
            "nodename nor servname provided",
            "getaddrinfo failed",
        )
    )


def _execute_process(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
    stdout_path: Path,
    stderr_path: Path,
    timeout: float,
    maximum_output_bytes: int,
) -> ProcessOutcome:
    with stdout_path.open("wb") as stdout_stream, stderr_path.open("wb") as stderr_stream:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=stdout_stream,
            stderr=stderr_stream,
            start_new_session=True,
        )
        timed_out = False
        try:
            returncode = process.wait(timeout=max(0.1, timeout))
        except subprocess.TimeoutExpired:
            timed_out = True
            if os.name == "nt":
                process.kill()
            else:
                os.killpg(process.pid, signal.SIGKILL)
            returncode = process.wait(timeout=10)
    stdout_limit = maximum_output_bytes // 2
    stderr_limit = maximum_output_bytes - stdout_limit
    return ProcessOutcome(
        returncode=returncode,
        stdout=_bounded_text(stdout_path, stdout_limit),
        stderr=_bounded_text(stderr_path, stderr_limit),
        timed_out=timed_out,
    )


def _safe_extract_environment(archive_path: Path, destination: Path, maximum_file_bytes: int) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            relative = PurePosixPath(member.name)
            if relative.is_absolute() or ".." in relative.parts or not relative.parts or relative.parts[0] != "venv":
                raise ValueError("Environment artifact contains an unsafe path")
            if member.size > maximum_file_bytes:
                raise ValueError("Environment artifact contains a file above the execution limit")
            if member.issym() or member.islnk():
                link = PurePosixPath(member.linkname)
                allowed_interpreter = member.issym() and member.linkname.startswith("/usr/local/bin/python")
                if link.is_absolute() and not allowed_interpreter:
                    raise ValueError("Environment artifact contains an unsafe absolute link")
                if not link.is_absolute() and ".." in (relative.parent / link).parts:
                    raise ValueError("Environment artifact contains an escaping link")
        if sys.version_info >= (3, 12):
            archive.extractall(destination, members=members, filter="fully_trusted")  # noqa: S202
        else:  # pragma: no cover - exercised by the Python 3.10/3.11 image contracts
            archive.extractall(destination, members=members)  # noqa: S202 - members are validated above


def _venv_python(environment_root: Path) -> Path:
    candidates = (environment_root / "venv" / "bin" / "python", environment_root / "venv" / "Scripts" / "python.exe")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise ValueError("Environment artifact does not contain a Python interpreter")


def _project_site_packages(environment_root: Path) -> tuple[Path, ...]:
    venv = environment_root / "venv"
    candidates = [venv / "Lib" / "site-packages"]
    candidates.extend((venv / "lib").glob("python*/site-packages"))
    return tuple(path for path in candidates if path.is_dir())


def _project_pytest_plugins(environment_root: Path) -> tuple[str, ...]:
    plugins: set[str] = set()
    site_packages = [str(path) for path in _project_site_packages(environment_root)]
    for distribution in distributions(path=site_packages):
        for entry_point in distribution.entry_points:
            if entry_point.group == "pytest11":
                plugins.add(entry_point.value.split(":", 1)[0])
    return tuple(sorted(plugins))


def _inside(root: Path, relative: str) -> Path:
    root = root.resolve()
    candidate = (root / Path(*PurePosixPath(relative).parts)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("Run path escapes the project source mount") from exc
    return candidate


def _coverage_config(spec: SandboxSpec, source_root: Path, output_root: Path) -> Path:
    source = _inside(source_root, spec.source_directory)
    if not source.exists():
        raise ValueError("Sandbox source_directory does not exist")
    branch = "True" if spec.coverage_mode == CoverageMode.STATEMENT_AND_BRANCH else "False"
    config = output_root / ".sandbox-coveragerc"
    config.write_text(
        "[run]\n"
        f"branch = {branch}\n"
        f"source = {source.as_posix()}\n"
        f"data_file = {(output_root / '.coverage').as_posix()}\n"
        "parallel = False\n"
        "[report]\n"
        "fail_under = 0\n"
        "show_missing = False\n",
        encoding="utf-8",
    )
    return config


def _sanitized_environment(
    spec: SandboxSpec,
    source_root: Path,
    environment_root: Path,
    output_root: Path,
) -> dict[str, str]:
    allowed = {name: os.environ[name] for name in spec.allowed_environment_variables if name in os.environ}
    source_directory = _inside(source_root, spec.source_directory)
    import_roots = {source_root, source_directory.parent}
    if source_directory.parts and source_directory.relative_to(source_root).parts[:1] == ("src",):
        import_roots.add(source_root / "src")
    import_roots.add(Path(__file__).resolve().parents[1])
    import_roots.update(_project_site_packages(environment_root))
    allowed.update(
        {
            "COVERAGE_FILE": str(output_root / ".coverage"),
            "HOME": str(output_root / "home"),
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": allowed.get("PYTHONHASHSEED", "0"),
            "PYTHONPATH": os.pathsep.join(str(path) for path in sorted(import_roots)),
            "SANDBOX_TEST_COUNTS_FILE": str(output_root / "test-counts.json"),
            "TMPDIR": str(output_root / "tmp"),
        }
    )
    for directory in (output_root / "home", output_root / "tmp", output_root / "pytest-tmp"):
        directory.mkdir(parents=True, exist_ok=True)
    return allowed


class _SymbolVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.stack: list[str] = []
        self.ranges: dict[str, tuple[int, int]] = {}

    def _visit_symbol(self, node) -> None:
        self.stack.append(node.name)
        self.ranges[".".join(self.stack)] = (node.lineno, node.end_lineno or node.lineno)
        self.generic_visit(node)
        self.stack.pop()

    def visit_ClassDef(self, node) -> None:  # noqa: N802 - ast.NodeVisitor API
        self._visit_symbol(node)

    def visit_FunctionDef(self, node) -> None:  # noqa: N802 - ast.NodeVisitor API
        self._visit_symbol(node)

    def visit_AsyncFunctionDef(self, node) -> None:  # noqa: N802 - ast.NodeVisitor API
        self._visit_symbol(node)


def _coverage_file_path(raw: str, source_root: Path) -> Path:
    path = Path(raw)
    candidate = path.resolve() if path.is_absolute() else (source_root / path).resolve()
    try:
        candidate.relative_to(source_root.resolve())
    except ValueError as exc:
        raise ValueError("Coverage output references a file outside the source mount") from exc
    return candidate


def _normalize_coverage(
    raw_path: Path,
    normalized_path: Path,
    *,
    spec: SandboxSpec,
    run_spec: RunSpec,
    source_root: Path,
    decision: RunnerDecision,
    force_zero_covered: bool,
) -> CoverageSummary:
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    raw_files = payload.get("files")
    if not isinstance(raw_files, dict):
        raise ValueError("Coverage JSON does not contain a files mapping")
    files: list[dict[str, object]] = []
    selected: dict[str, object] | None = None
    selected_path: Path | None = None
    target_path = _inside(source_root, run_spec.source_file) if run_spec.source_file else None
    for raw_name, details in sorted(raw_files.items()):
        path = _coverage_file_path(raw_name, source_root)
        if not isinstance(details, dict):
            raise ValueError("Coverage JSON contains invalid file details")
        relative = path.relative_to(source_root.resolve()).as_posix()
        record = {
            "path": relative,
            "executed_lines": sorted(int(item) for item in details.get("executed_lines", ())),
            "missing_lines": sorted(int(item) for item in details.get("missing_lines", ())),
            "executed_branches": sorted(details.get("executed_branches", ())),
            "missing_branches": sorted(details.get("missing_branches", ())),
        }
        files.append(record)
        if target_path is not None and path == target_path:
            selected = record
            selected_path = path
    totals = payload.get("totals", {})
    if target_path is not None:
        if selected is None or selected_path is None:
            raise ValueError("Coverage output does not contain the requested source_file")
        tree = ast.parse(selected_path.read_text(encoding="utf-8"), filename=str(selected_path))
        visitor = _SymbolVisitor()
        visitor.visit(tree)
        if run_spec.symbol not in visitor.ranges:
            raise ValueError("Requested symbol does not exist in source_file")
        first, last = visitor.ranges[run_spec.symbol]
        executed_lines = {line for line in selected["executed_lines"] if first <= line <= last}
        missing_lines = {line for line in selected["missing_lines"] if first <= line <= last}
        branches = [
            branch
            for branch in (*selected["executed_branches"], *selected["missing_branches"])
            if isinstance(branch, list) and len(branch) == 2 and first <= int(branch[0]) <= last
        ]
        executed_branches = [
            branch
            for branch in selected["executed_branches"]
            if isinstance(branch, list) and len(branch) == 2 and first <= int(branch[0]) <= last
        ]
        covered_statements = len(executed_lines)
        total_statements = len(executed_lines | missing_lines)
        covered_branches = len(executed_branches)
        total_branches = len(branches)
    else:
        covered_statements = int(totals.get("covered_lines", 0))
        total_statements = int(totals.get("num_statements", 0))
        covered_branches = int(totals.get("covered_branches", 0))
        total_branches = int(totals.get("num_branches", 0))
    if spec.coverage_mode == CoverageMode.STATEMENT:
        covered_branches = total_branches = 0
    if force_zero_covered:
        covered_statements = covered_branches = 0
    summary = CoverageSummary(covered_statements, total_statements, covered_branches, total_branches)
    normalized = {
        "schema_version": NORMALIZED_COVERAGE_VERSION,
        "run_id": run_spec.run_id,
        "environment_fingerprint": run_spec.environment_fingerprint,
        "runner": {
            "profile": decision.profile.value,
            "pytest_version": decision.pytest_version,
            "coverage_version": decision.coverage_version,
        },
        "target": {"source_file": run_spec.source_file, "symbol": run_spec.symbol},
        "coverage": summary.as_dict(),
        "files": files,
    }
    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_path.write_text(json.dumps(normalized, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    return summary


def _test_counts(path: Path) -> TestCounts:
    if not path.is_file():
        return TestCounts()
    try:
        return TestCounts.from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return TestCounts()


def _failure_result(
    run_spec: RunSpec,
    *,
    stage: FailureStage,
    error_code: str,
    decision: RunnerDecision | None = None,
    exit_code: int | None = None,
    counts: TestCounts | None = None,
    coverage: CoverageSummary | None = None,
    coverage_artifact: str | None = None,
    stdout: str = "",
    stderr: str = "",
    duration: float = 0.0,
) -> SandboxResult:
    contract_exit_code = -1 if exit_code is not None and exit_code < 0 else exit_code
    return SandboxResult(
        run_id=run_spec.run_id,
        status=SandboxStatus.FAILED,
        environment_fingerprint=run_spec.environment_fingerprint,
        exit_code=contract_exit_code,
        failure_stage=stage,
        error_code=error_code,
        retryable=False,
        test_counts=counts or TestCounts(),
        coverage=coverage,
        coverage_artifact=coverage_artifact,
        stdout=redact_sensitive_text(stdout),
        stderr=redact_sensitive_text(stderr),
        duration_seconds=duration,
        runner_profile=decision.profile if decision else None,
        pytest_version=decision.pytest_version if decision else None,
        coverage_version=decision.coverage_version if decision else None,
    )


def execute_run(
    spec: SandboxSpec,
    run_spec: RunSpec,
    *,
    manifest_path: Path,
    archive_path: Path,
    source_root: Path,
    output_root: Path,
    workspace_root: Path,
    tests_root: Path | None = None,
    managed_python: Path | None = None,
) -> SandboxResult:
    """Execute one test run; all inputs are validated contract objects."""

    started = time.monotonic()
    output_root.mkdir(parents=True, exist_ok=True)
    try:
        manifest = ArtifactManifest.from_dict(json.loads(manifest_path.read_text(encoding="utf-8")))
        if manifest.fingerprint != run_spec.environment_fingerprint:
            raise ValueError("Environment artifact fingerprint does not match RunSpec")
        if _sha256_file(archive_path) != manifest.artifact_sha256:
            raise ValueError("Environment artifact hash does not match manifest")
        inventory = {item.name: item.version for item in manifest.inventory}
        decision = select_runner_profile(inventory)
        if decision.profile == RunnerProfile.COMPATIBILITY_FALLBACK:
            return _failure_result(
                run_spec,
                stage=FailureStage.COLLECT,
                error_code=decision.error_code or "UNSUPPORTED_PROJECT_RUNNER",
                decision=decision,
                stderr=decision.reason,
                duration=time.monotonic() - started,
            )
        runner_identity_matches = (
            manifest.runner.profile == decision.profile.value
            and manifest.runner.pytest_version == decision.pytest_version
            and manifest.runner.coverage_version == decision.coverage_version
        )
        if decision.profile != spec.runner_profile or not runner_identity_matches:
            return _failure_result(
                run_spec,
                stage=FailureStage.COLLECT,
                error_code="RUNNER_PROFILE_MISMATCH",
                decision=decision,
                stderr="Resolved inventory, SandboxSpec and artifact runner profile do not match",
                duration=time.monotonic() - started,
            )
        if manifest.image.python_minor != spec.requested_python:
            raise ValueError("SandboxSpec Python version does not match environment artifact")
        _safe_extract_environment(archive_path, workspace_root, spec.resource_limits.maximum_file_bytes)
        native_python = _venv_python(workspace_root)
        if decision.profile == RunnerProfile.PROJECT_NATIVE:
            python = native_python
        else:
            # Do not resolve the venv interpreter symlink: doing so bypasses
            # the managed environment and loses its pytest/coverage packages.
            python = managed_python or Path(sys.executable)
        config = _coverage_config(spec, source_root, output_root)
        environment = _sanitized_environment(spec, source_root, workspace_root, output_root)
        plugin_arguments: list[str] = []
        if decision.profile == RunnerProfile.SANDBOX_MANAGED:
            environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
            for plugin in _project_pytest_plugins(workspace_root):
                plugin_arguments.extend(["-p", plugin])
        test_paths = []
        selected_tests_root = tests_root or source_root
        for relative in run_spec.test_paths:
            test_path = _inside(selected_tests_root, relative)
            if not test_path.exists():
                raise ValueError(f"RunSpec test path does not exist: {relative}")
            test_paths.append(str(test_path))
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError, tarfile.TarError) as exc:
        return _failure_result(
            run_spec,
            stage=FailureStage.INTERNAL,
            error_code="SANDBOX_INPUT_INVALID",
            stderr=str(exc),
            duration=time.monotonic() - started,
        )

    pytest_command = [
        str(python),
        "-m",
        "coverage",
        "run",
        f"--rcfile={config}",
        "-m",
        "pytest",
        "-p",
        "cloud.sandbox_pytest_plugin",
        "-p",
        "no:cacheprovider",
        "--capture=no",
        *plugin_arguments,
        "--basetemp",
        str(output_root / "pytest-tmp"),
        "--rootdir",
        str(source_root),
        "-o",
        f"python_files={run_spec.test_pattern}",
        *test_paths,
    ]
    pytest_outcome = _execute_process(
        pytest_command,
        cwd=source_root,
        environment=environment,
        stdout_path=output_root / "pytest.stdout",
        stderr_path=output_root / "pytest.stderr",
        timeout=spec.resource_limits.timeout_seconds,
        maximum_output_bytes=spec.resource_limits.maximum_output_bytes,
    )
    counts = _test_counts(output_root / "test-counts.json")
    if pytest_outcome.timed_out:
        return _failure_result(
            run_spec,
            stage=FailureStage.TIMEOUT,
            error_code="TEST_TIMEOUT",
            decision=decision,
            exit_code=-1,
            counts=counts,
            stdout=pytest_outcome.stdout,
            stderr=pytest_outcome.stderr,
            duration=time.monotonic() - started,
        )
    combined = f"{pytest_outcome.stdout}\n{pytest_outcome.stderr}".casefold()
    collection_error = any(
        marker in combined
        for marker in ("error collecting", "errors during collection", "collection error", "syntaxerror")
    )
    if pytest_outcome.returncode in {1, 2, 4} and collection_error:
        return _failure_result(
            run_spec,
            stage=FailureStage.COLLECT,
            error_code=(
                "EXECUTION_NETWORK_DENIED" if _network_denied_during_collection(combined) else "TEST_COLLECTION_FAILED"
            ),
            decision=decision,
            exit_code=pytest_outcome.returncode,
            counts=counts,
            stdout=pytest_outcome.stdout,
            stderr=pytest_outcome.stderr,
            duration=time.monotonic() - started,
        )
    if pytest_outcome.returncode not in {0, 1, 5}:
        return _failure_result(
            run_spec,
            stage=FailureStage.INTERNAL,
            error_code="TEST_RUNNER_INTERNAL",
            decision=decision,
            exit_code=pytest_outcome.returncode,
            counts=counts,
            stdout=pytest_outcome.stdout,
            stderr=pytest_outcome.stderr,
            duration=time.monotonic() - started,
        )

    raw_coverage = output_root / "coverage" / "coverage.json"
    normalized_coverage = output_root / "coverage" / "normalized.json"
    raw_coverage.parent.mkdir(parents=True, exist_ok=True)
    coverage_command = [
        str(python),
        "-m",
        "coverage",
        "json",
        f"--rcfile={config}",
        "--fail-under=0",
        "-o",
        str(raw_coverage),
    ]
    elapsed = time.monotonic() - started
    coverage_outcome = _execute_process(
        coverage_command,
        cwd=source_root,
        environment=environment,
        stdout_path=output_root / "coverage.stdout",
        stderr_path=output_root / "coverage.stderr",
        timeout=max(1.0, spec.resource_limits.timeout_seconds - elapsed),
        maximum_output_bytes=spec.resource_limits.maximum_output_bytes,
    )
    if coverage_outcome.timed_out:
        return _failure_result(
            run_spec,
            stage=FailureStage.TIMEOUT,
            error_code="COVERAGE_TIMEOUT",
            decision=decision,
            exit_code=pytest_outcome.returncode,
            counts=counts,
            stdout=pytest_outcome.stdout,
            stderr=pytest_outcome.stderr + coverage_outcome.stderr,
            duration=time.monotonic() - started,
        )
    if coverage_outcome.returncode != 0 or not raw_coverage.is_file():
        return _failure_result(
            run_spec,
            stage=FailureStage.COVERAGE,
            error_code="COVERAGE_EXPORT_FAILED",
            decision=decision,
            exit_code=pytest_outcome.returncode,
            counts=counts,
            stdout=pytest_outcome.stdout,
            stderr=pytest_outcome.stderr + coverage_outcome.stderr,
            duration=time.monotonic() - started,
        )
    try:
        summary = _normalize_coverage(
            raw_coverage,
            normalized_coverage,
            spec=spec,
            run_spec=run_spec,
            source_root=source_root,
            decision=decision,
            force_zero_covered=pytest_outcome.returncode == 1,
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError, SyntaxError) as exc:
        return _failure_result(
            run_spec,
            stage=FailureStage.COVERAGE,
            error_code="COVERAGE_ARTIFACT_INVALID",
            decision=decision,
            exit_code=pytest_outcome.returncode,
            counts=counts,
            stdout=pytest_outcome.stdout,
            stderr=f"{pytest_outcome.stderr}\n{exc}",
            duration=time.monotonic() - started,
        )
    duration = time.monotonic() - started
    if pytest_outcome.returncode == 1:
        return _failure_result(
            run_spec,
            stage=FailureStage.TEST,
            error_code="TESTS_FAILED",
            decision=decision,
            exit_code=1,
            counts=counts,
            coverage=summary,
            coverage_artifact="coverage/normalized.json",
            stdout=pytest_outcome.stdout,
            stderr=pytest_outcome.stderr,
            duration=duration,
        )
    return SandboxResult(
        run_id=run_spec.run_id,
        status=SandboxStatus.SUCCEEDED,
        environment_fingerprint=run_spec.environment_fingerprint,
        exit_code=pytest_outcome.returncode,
        test_counts=counts,
        coverage=summary,
        coverage_artifact="coverage/normalized.json",
        stdout=pytest_outcome.stdout,
        stderr=pytest_outcome.stderr,
        duration_seconds=duration,
        runner_profile=decision.profile,
        pytest_version=decision.pytest_version,
        coverage_version=decision.coverage_version,
    )


def clean_execution_workspace(workspace_root: Path) -> None:
    """Remove only the dedicated execution workspace supplied by the caller."""

    if not workspace_root.exists():
        return
    # Docker mounts the tmpfs at ``workspace_root``.  Its contents are ours to
    # remove, but the mount point itself cannot be unlinked from inside the
    # container.  Removing children first also keeps the helper useful for a
    # normal directory in unit tests, where the empty root can still be removed.
    for child in workspace_root.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()
    try:
        workspace_root.rmdir()
    except OSError:
        if any(workspace_root.iterdir()):
            raise
