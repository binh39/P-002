"""Build and restore persistent Python runtime bundles for uploaded projects."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import time
import venv
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath

MAX_ARCHIVE_ENTRIES = 20_000
MAX_UNCOMPRESSED_BYTES = 250 * 1024 * 1024
MAX_FILE_BYTES = 25 * 1024 * 1024
RUNTIME_PROTOCOL_VERSION = 3
RUNTIME_TOOL_PACKAGES = (
    "pytest==9.1.1",
    "pytest-repeat==0.9.4",
    "coverage==7.15.2",
    "slipcover==1.0.18",
)
DEPENDENCY_FILES = (
    "uv.lock",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-test.txt",
    "test-requirements.txt",
    "setup.py",
    "setup.cfg",
)
LEGACY_REQUIREMENT_FILES = (
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-test.txt",
    "test-requirements.txt",
)
_PACKAGE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(slots=True)
class CommandResult:
    name: str
    command: list[str]
    return_code: int | None
    duration_seconds: float
    timed_out: bool = False
    output: str = ""


@dataclass(frozen=True, slots=True)
class RuntimeProjectSpec:
    project_id: str
    archive: Path
    configured_source: str = "src"
    configured_tests: str = "tests"


@dataclass(slots=True)
class RuntimeProjectResult:
    project_root: str = ""
    source_directory: str = ""
    test_directory: str = ""
    dependency_files: list[str] = field(default_factory=list)
    collected_tests: int = 0
    statement_coverage: float | None = None
    branch_coverage: float | None = None


@dataclass(slots=True)
class RuntimeResult:
    status: str
    project_root: str = ""
    source_directory: str = ""
    test_directory: str = ""
    dependency_files: list[str] = field(default_factory=list)
    install_strategy: str = ""
    collected_tests: int = 0
    statement_coverage: float | None = None
    branch_coverage: float | None = None
    commands: list[CommandResult] = field(default_factory=list)
    projects: dict[str, RuntimeProjectResult] = field(default_factory=dict)
    dependency_fingerprint: str | None = None
    bundle_object: str | None = None
    error: str | None = None
    protocol_version: int = RUNTIME_PROTOCOL_VERSION

    def as_dict(self) -> dict:
        return asdict(self)


def safe_extract_zip(archive: Path, destination: Path) -> None:
    """Extract a ZIP without following links or accepting path traversal."""
    destination.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    total = 0
    with zipfile.ZipFile(archive) as bundle:
        infos = bundle.infolist()
        if len(infos) > MAX_ARCHIVE_ENTRIES:
            raise ValueError(f"ZIP contains more than {MAX_ARCHIVE_ENTRIES} entries")
        for info in infos:
            raw = info.filename.replace("\\", "/")
            path = PurePosixPath(raw)
            if not raw or path.is_absolute() or ".." in path.parts:
                raise ValueError(f"Unsafe ZIP path: {raw!r}")
            normalized = "/".join(part for part in path.parts if part not in {"", "."})
            key = normalized.casefold()
            if key in seen:
                raise ValueError(f"Duplicate ZIP path: {normalized}")
            seen.add(key)
            if info.flag_bits & 0x1:
                raise ValueError(f"Encrypted ZIP entry is not supported: {normalized}")
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ValueError(f"Symbolic links are not allowed in ZIP files: {normalized}")
            if info.file_size > MAX_FILE_BYTES:
                raise ValueError(f"ZIP entry exceeds {MAX_FILE_BYTES} bytes: {normalized}")
            total += info.file_size
            if total > MAX_UNCOMPRESSED_BYTES:
                raise ValueError("ZIP uncompressed size exceeds the runtime limit")
            target = destination.joinpath(*PurePosixPath(normalized).parts)
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(info) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)


def safe_extract_runtime_bundle(bundle: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with tarfile.open(bundle, "r:gz") as archive:
        for member in archive.getmembers():
            if member.issym() or member.islnk() or member.isdev():
                raise ValueError(f"Runtime bundle contains an unsupported entry: {member.name}")
            target = (root / member.name).resolve()
            if target != root and root not in target.parents:
                raise ValueError(f"Runtime bundle path escapes destination: {member.name}")
        archive.extractall(root, filter="data")
    python = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():
        raise RuntimeError("Runtime bundle does not contain a usable Python environment")
    return python


def create_runtime_bundle(venv_dir: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Linux virtual environments normally use symlinks for ``bin/python``.
    # Dereference them so the immutable artifact contains regular files and can
    # be restored by the deliberately link-rejecting extractor.
    with tarfile.open(destination, "w:gz", dereference=True) as archive:
        archive.add(venv_dir, arcname=".venv", recursive=True)


def find_project_root(extracted: Path) -> Path:
    ignored = {"__MACOSX", ".git"}
    children = [item for item in extracted.iterdir() if item.name not in ignored]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return extracted


def detect_layout(root: Path, configured_source: str = "src", configured_tests: str = "tests") -> tuple[Path, Path]:
    source = _safe_relative(root, configured_source)
    if not source.is_dir() or not any(source.rglob("*.py")):
        source = _detect_source(root)
    tests = _safe_relative(root, configured_tests)
    if not tests.is_dir():
        tests = next((item for item in (root / "test", root / "tests") if item.is_dir()), root / "tests")
    return source, tests


def _detect_source(root: Path) -> Path:
    src = root / "src"
    if src.is_dir() and any(src.rglob("*.py")):
        packages = [item for item in src.iterdir() if item.is_dir() and (item / "__init__.py").is_file()]
        return packages[0] if len(packages) == 1 else src
    packages = [
        item
        for item in root.iterdir()
        if item.is_dir() and _PACKAGE_NAME.match(item.name) and (item / "__init__.py").is_file()
    ]
    if packages:
        return sorted(packages)[0]
    if any(root.glob("*.py")):
        return root
    raise ValueError("No importable Python source directory was detected")


def _safe_relative(root: Path, value: str) -> Path:
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"Configured path escapes the project root: {value}") from exc
    return candidate


def prepare_environment(
    specs: list[RuntimeProjectSpec],
    workspace: Path,
    *,
    timeout_seconds: int = 900,
    maximum_output_bytes: int = 10 * 1024 * 1024,
    expected_python: str | None = None,
    persistent_venv: Path | None = None,
) -> tuple[RuntimeResult, Path | None]:
    """Resolve all projects together and accept the environment atomically."""
    result = RuntimeResult(status="runtime_failed")
    try:
        if not specs:
            raise ValueError("Runtime environment requires at least one project")
        actual_python = f"{sys.version_info.major}.{sys.version_info.minor}"
        if expected_python and expected_python != actual_python:
            raise RuntimeError(
                f"Environment requests Python {expected_python}, but the runtime provides Python {actual_python}"
            )
        if len({spec.project_id for spec in specs}) != len(specs):
            raise ValueError("Runtime environment contains duplicate project IDs")

        workspace.mkdir(parents=True, exist_ok=True)
        roots: dict[str, Path] = {}
        sources: dict[str, Path] = {}
        tests: dict[str, Path] = {}
        digest = hashlib.sha256(f"runtime-v{RUNTIME_PROTOCOL_VERSION}|python-{actual_python}".encode())
        for spec in sorted(specs, key=lambda item: item.project_id):
            digest.update(spec.project_id.encode())
            digest.update(spec.configured_source.encode())
            digest.update(spec.configured_tests.encode())
            digest.update(spec.archive.read_bytes())
            extracted = workspace / "projects" / spec.project_id
            safe_extract_zip(spec.archive, extracted)
            root = find_project_root(extracted).resolve()
            source, test_dir = detect_layout(root, spec.configured_source, spec.configured_tests)
            dependency_files = [name for name in DEPENDENCY_FILES if (root / name).is_file()]
            roots[spec.project_id] = root
            sources[spec.project_id] = source
            tests[spec.project_id] = test_dir
            result.projects[spec.project_id] = RuntimeProjectResult(
                project_root=str(root),
                source_directory=source.relative_to(root).as_posix() or ".",
                test_directory=test_dir.relative_to(root).as_posix() if test_dir.exists() else spec.configured_tests,
                dependency_files=dependency_files,
            )
        result.dependency_fingerprint = digest.hexdigest()

        venv_dir = (persistent_venv or workspace / ".venv").resolve()
        if venv_dir.exists():
            shutil.rmtree(venv_dir)
        deadline = time.monotonic() + timeout_seconds
        uv = shutil.which("uv")
        if uv:
            _run(
                result,
                "create shared environment",
                [uv, "venv", "--python", sys.executable, str(venv_dir)],
                workspace,
                deadline,
                maximum_output_bytes,
            )
        else:
            venv.EnvBuilder(with_pip=True, system_site_packages=True).create(venv_dir)
        python = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

        requirements: list[Path] = []
        installable_roots: list[Path] = []
        for project_id, root in roots.items():
            if (root / "pyproject.toml").is_file() and uv:
                exported = workspace / "resolved" / f"{project_id}.txt"
                exported.parent.mkdir(parents=True, exist_ok=True)
                export_command = [uv, "export"]
                if (root / "uv.lock").is_file():
                    export_command.append("--frozen")
                export_command.extend(
                    [
                        "--all-groups",
                        "--no-emit-project",
                        "--format",
                        "requirements-txt",
                        "--output-file",
                        str(exported),
                    ]
                )
                _run(
                    result,
                    f"export {project_id} lock",
                    export_command,
                    root,
                    deadline,
                    maximum_output_bytes,
                )
                requirements.append(exported)
            else:
                requirements.extend(root / name for name in LEGACY_REQUIREMENT_FILES if (root / name).is_file())
            if any((root / name).is_file() for name in ("pyproject.toml", "setup.py", "setup.cfg")):
                installable_roots.append(root)

        if requirements or installable_roots or uv:
            command = (
                [uv, "pip", "install", "--python", str(python)]
                if uv
                else [str(python), "-m", "pip", "install", "--disable-pip-version-check"]
            )
            for requirement in requirements:
                command.extend(["-r", str(requirement)])
            if uv:
                command.extend(RUNTIME_TOOL_PACKAGES)
            command.extend(str(root) for root in installable_roots)
            _run(result, "resolve shared dependencies", command, workspace, deadline, maximum_output_bytes)
            check = [uv, "pip", "check", "--python", str(python)] if uv else [str(python), "-m", "pip", "check"]
            _run(result, "verify dependency compatibility", check, workspace, deadline, maximum_output_bytes)
            result.install_strategy = "uv shared resolution" if uv else "pip shared resolution"
        else:
            result.install_strategy = "PYTHONPATH (no dependency manifest)"

        for project_id in roots:
            project_result = result.projects[project_id]
            pytest_target = tests[project_id] if tests[project_id].is_dir() else roots[project_id]
            collect = _run(
                result,
                f"collect tests for {project_id}",
                [str(python), "-m", "pytest", "--collect-only", "-q", str(pytest_target)],
                roots[project_id],
                deadline,
                maximum_output_bytes,
                allowed_return_codes=(0, 5),
                pytest_plugin_autoload=bool(uv),
            )
            project_result.collected_tests = _parse_collected_tests(collect.output)
            coverage_data = workspace / "coverage" / f".coverage-{project_id}"
            coverage_json = workspace / "coverage" / f"{project_id}.json"
            coverage_json.parent.mkdir(parents=True, exist_ok=True)
            _run(
                result,
                f"baseline tests for {project_id}",
                [
                    str(python),
                    "-m",
                    "coverage",
                    "run",
                    "--branch",
                    f"--data-file={coverage_data}",
                    f"--source={sources[project_id]}",
                    "-m",
                    "pytest",
                    "-q",
                    str(pytest_target),
                ],
                roots[project_id],
                deadline,
                maximum_output_bytes,
                allowed_return_codes=(0, 5),
                pytest_plugin_autoload=bool(uv),
            )
            _run(
                result,
                f"coverage report for {project_id}",
                [
                    str(python),
                    "-m",
                    "coverage",
                    "json",
                    f"--data-file={coverage_data}",
                    "-o",
                    str(coverage_json),
                ],
                roots[project_id],
                deadline,
                maximum_output_bytes,
            )
            coverage = json.loads(coverage_json.read_text(encoding="utf-8"))["totals"]
            project_result.statement_coverage = float(coverage.get("percent_covered", 0.0)) / 100.0
            branches = int(coverage.get("num_branches", 0))
            project_result.branch_coverage = int(coverage.get("covered_branches", 0)) / branches if branches else 1.0

        first = result.projects[specs[0].project_id]
        result.project_root = first.project_root
        result.source_directory = first.source_directory
        result.test_directory = first.test_directory
        result.dependency_files = first.dependency_files
        result.collected_tests = first.collected_tests
        result.statement_coverage = first.statement_coverage
        result.branch_coverage = first.branch_coverage
        result.status = "runtime_ready"
        return result, python
    except Exception as exc:  # noqa: BLE001 - persisted as a bounded user-facing diagnostic
        result.error = str(exc)[-4000:]
        return result, None


def prepare_runtime(
    archive: Path,
    workspace: Path,
    *,
    configured_source: str = "src",
    configured_tests: str = "tests",
    timeout_seconds: int = 900,
    maximum_output_bytes: int = 10 * 1024 * 1024,
    expected_python: str | None = None,
) -> tuple[RuntimeResult, Path | None]:
    return prepare_environment(
        [RuntimeProjectSpec("project", archive, configured_source, configured_tests)],
        workspace,
        timeout_seconds=timeout_seconds,
        maximum_output_bytes=maximum_output_bytes,
        expected_python=expected_python,
    )


def _run(
    result: RuntimeResult,
    name: str,
    command: list[str],
    cwd: Path,
    deadline: float,
    output_limit: int,
    *,
    allowed_return_codes: tuple[int, ...] = (0,),
    pytest_plugin_autoload: bool = False,
) -> CommandResult:
    remaining = max(1.0, deadline - time.monotonic())
    started = time.monotonic()
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONHASHSEED": "0",
        "TZ": "UTC",
        "PIP_NO_INPUT": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
    }
    if not pytest_plugin_autoload:
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    for env_name in (
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "PATHEXT",
        "TEMP",
        "TMP",
        "LANG",
        "LC_ALL",
        "SSL_CERT_FILE",
    ):
        if value := os.environ.get(env_name):
            env[env_name] = value
    if (cwd / "src").is_dir():
        env["PYTHONPATH"] = str(cwd / "src")
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=remaining,
            check=False,
        )
        output = completed.stdout[:output_limit].decode("utf-8", errors="replace")
        item = CommandResult(name, command, completed.returncode, time.monotonic() - started, output=output)
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or b"")[:output_limit].decode("utf-8", errors="replace")
        item = CommandResult(name, command, None, time.monotonic() - started, timed_out=True, output=output)
    result.commands.append(item)
    if item.timed_out:
        raise RuntimeError(f"{name} timed out")
    if item.return_code not in allowed_return_codes:
        detail = item.output[-2000:]
        if name == "resolve shared dependencies":
            raise RuntimeError(f"Dependency conflict prevented this project from joining the environment: {detail}")
        raise RuntimeError(f"{name} failed with exit code {item.return_code}: {detail}")
    return item


def _parse_collected_tests(output: str) -> int:
    matches = re.findall(r"(\d+)\s+(?:tests?|items?)\s+collected", output)
    if matches:
        return int(matches[-1])
    return len(re.findall(r"::test[^\s]*", output))
