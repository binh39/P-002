"""Build and restore persistent Python runtime bundles for uploaded projects."""

from __future__ import annotations

import ast
import configparser
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

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import Version

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 runtime images use the backport.
    import tomli as tomllib

from src.optimization.project_setup import prepare_project

MAX_ARCHIVE_ENTRIES = 20_000
MAX_UNCOMPRESSED_BYTES = 250 * 1024 * 1024
MAX_FILE_BYTES = 25 * 1024 * 1024
# Protocol 11 describes the prepared project capsule. Protocol 12 is emitted
# only after the trusted factory has baked that capsule and source archive into
# a project-specific OCI image and created its dedicated worker job.
RUNTIME_PROTOCOL_VERSION = 11
RUNTIME_TOOL_PACKAGES = (
    "pytest>=7.4,<10",
    "pytest-asyncio>=0.23,<2",
    "pytest-repeat>=0.9,<1",
    "pytest-timeout>=2.3,<3",
    "coverage>=7,<8",
    "slipcover>=1,<2",
)
MAX_ADMISSION_BASELINE_TESTS = 250
ADMISSION_COMMAND_TIMEOUT_SECONDS = 120
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
_NON_SOURCE_PACKAGE_NAMES = {
    "benchmarks",
    "docs",
    "examples",
    "migrations",
    "scripts",
    "test",
    "tests",
}
_TEST_EXTRA_NAMES = {"dev", "development", "test", "testing", "tests", "unit", "units"}


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
    runtime_digest: str | None = None
    python_version: str | None = None
    runtime_image: str | None = None
    runtime_worker_job: str | None = None
    source_archive_sha256: str | None = None
    runtime_bundle_sha256: str | None = None
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
                # Git-generated ZIP files may contain repository symlinks.
                # Ignoring them is safe because no link is materialized or
                # followed inside the runtime workspace.
                continue
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
    configured_parts = {part.casefold() for part in PurePosixPath(configured_source.replace("\\", "/")).parts}
    if configured_parts.intersection(_NON_SOURCE_PACKAGE_NAMES) or not source.is_dir() or not any(source.rglob("*.py")):
        source = _detect_source(root)
    tests = _safe_relative(root, configured_tests)
    if not tests.is_dir():
        tests = next((item for item in (root / "test", root / "tests") if item.is_dir()), root / "tests")
    return source, tests


def _runtime_test_directory(root: Path, tests: Path) -> Path:
    """Choose a bounded unit-test target for runtime admission.

    Large repositories often keep executable integration harnesses below a
    singular ``test/`` directory. Importing those files with plain pytest can
    execute command-line entry points during collection. Prefer an explicit
    unit-test subtree and represent integration-only/no-test projects with an
    empty directory instead of ever collecting the repository root.
    """
    if tests.is_dir():
        for name in ("units", "unit"):
            unit_tests = tests / name
            if unit_tests.is_dir():
                return unit_tests
        if not (tests / "integration").is_dir():
            return tests

    empty_tests = root / ".promptopt-empty-tests"
    empty_tests.mkdir(parents=True, exist_ok=True)
    return empty_tests


def _detect_source(root: Path) -> Path:
    # Python projects commonly place import packages under src/ or lib/.
    # Treat these as generic source containers rather than assuming src/ only.
    for container_name in ("src", "lib", "python"):
        container = root / container_name
        if not container.is_dir() or not any(container.rglob("*.py")):
            continue
        packages = [item for item in container.iterdir() if item.is_dir() and (item / "__init__.py").is_file()]
        return packages[0] if len(packages) == 1 else container
    packages = [
        item
        for item in root.iterdir()
        if item.is_dir()
        and item.name.casefold() not in _NON_SOURCE_PACKAGE_NAMES
        and _PACKAGE_NAME.match(item.name)
        and (item / "__init__.py").is_file()
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


def _dependency_group_names(pyproject: Path) -> list[str]:
    try:
        payload = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return []
    groups = payload.get("dependency-groups", {})
    return sorted(str(name) for name in groups) if isinstance(groups, dict) else []


def _validate_project_python(root: Path, project_id: str) -> None:
    """Fail before dependency installation when project metadata is incompatible."""
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return
    try:
        payload = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        # Dependency resolution will report malformed project metadata with its
        # native diagnostic. Do not guess requirements from an unreadable file.
        return
    project = payload.get("project", {})
    requirement = project.get("requires-python") if isinstance(project, dict) else None
    if requirement is None:
        return
    if not isinstance(requirement, str) or not requirement.strip():
        raise ValueError(f"Project {project_id} has an invalid [project].requires-python value")
    try:
        supported = SpecifierSet(requirement)
    except InvalidSpecifier as exc:
        raise ValueError(f"Project {project_id} has an invalid requires-python specifier: {requirement!r}") from exc

    actual = Version(".".join(str(part) for part in sys.version_info[:3]))
    if actual not in supported:
        raise RuntimeError(
            f"Project {project_id} requires Python {requirement}, but the selected runtime "
            f"provides Python {actual}. Choose a runtime image with a compatible Python "
            "version, or upload a project revision that supports this runtime."
        )


def _test_requirement_files(root: Path, tests: Path) -> list[Path]:
    """Return dependency manifests declared for the selected test suite.

    Some repositories keep unit-test requirements in their test tooling tree
    instead of a root ``requirements-test.txt`` (for example under a
    ``requirements/units.txt`` directory). Select manifests by the actual test
    suite name so runtime preparation does not install unrelated integration,
    documentation, or release dependencies.
    """
    if tests.name == ".promptopt-empty-tests":
        return []

    suite = tests.name.casefold()
    suite_names = {suite}
    if suite.endswith("s"):
        suite_names.add(suite[:-1])
    else:
        suite_names.add(f"{suite}s")

    candidates = [tests / name for name in LEGACY_REQUIREMENT_FILES]
    for requirements_dir in root.rglob("requirements"):
        if not requirements_dir.is_dir():
            continue
        candidates.extend(requirements_dir / f"{name}.txt" for name in sorted(suite_names))

    unique: dict[Path, None] = {}
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.is_file() and resolved != (root / "requirements.txt").resolve():
            unique[resolved] = None
    return sorted(unique, key=lambda path: path.as_posix())


def _split_requirement_block(value: str) -> list[str]:
    """Parse the newline-oriented dependency syntax used by setup.cfg."""
    return [
        line.strip()
        for line in value.splitlines()
        if line.strip() and not line.lstrip().startswith(("#", "-r ", "--requirement "))
    ]


def _selected_extra_requirements(name: str, items: object) -> list[str]:
    """Normalize test extras and legacy environment-marker extras."""
    if isinstance(items, str):
        values = _split_requirement_block(items)
    elif isinstance(items, (list, tuple)):
        values = [str(item).strip() for item in items if str(item).strip()]
    else:
        return []
    normalized = name.strip()
    if normalized.casefold() in _TEST_EXTRA_NAMES:
        return values
    if normalized.startswith(":"):
        marker = normalized[1:].strip()
        return [f"{value}; {marker}" if ";" not in value else value for value in values]
    return []


def _literal_setup_value(node: ast.AST, assignments: dict[str, ast.AST]) -> object:
    """Evaluate only inert setup.py literals; repository code is never executed."""
    if isinstance(node, ast.Name) and node.id in assignments:
        return _literal_setup_value(assignments[node.id], assignments)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return [_literal_setup_value(item, assignments) for item in node.elts]
    if isinstance(node, ast.Dict):
        return {
            _literal_setup_value(key, assignments): _literal_setup_value(value, assignments)
            for key, value in zip(node.keys, node.values, strict=True)
            if key is not None
        }
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _literal_setup_value(node.left, assignments)
        right = _literal_setup_value(node.right, assignments)
        if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
            return [*left, *right]
        if isinstance(left, str) and isinstance(right, str):
            return left + right
        raise ValueError("unsupported setup.py addition")
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"list", "set", "tuple"}
        and len(node.args) == 1
        and not node.keywords
    ):
        value = _literal_setup_value(node.args[0], assignments)
        if isinstance(value, (list, tuple, set)):
            return list(value)
    raise ValueError("unsupported dynamic setup.py expression")


def _setup_keyword_values(tree: ast.Module, assignments: dict[str, ast.AST]) -> dict[str, ast.AST]:
    """Find direct setup keywords and static ``setup(**mapping)`` mutations."""
    mappings: dict[str, dict[str, ast.AST]] = {}
    for statement in tree.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
            continue
        target = statement.targets[0]
        if not isinstance(target, ast.Subscript) or not isinstance(target.value, ast.Name):
            continue
        try:
            key = _literal_setup_value(target.slice, assignments)
        except ValueError:
            continue
        if isinstance(key, str):
            mappings.setdefault(target.value.id, {})[key] = statement.value

    setup_call = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and (
                (isinstance(node.func, ast.Name) and node.func.id == "setup")
                or (isinstance(node.func, ast.Attribute) and node.func.attr == "setup")
            )
        ),
        None,
    )
    if setup_call is None:
        return {}

    keywords = {item.arg: item.value for item in setup_call.keywords if item.arg}
    for item in setup_call.keywords:
        if item.arg is None and isinstance(item.value, ast.Name):
            keywords.update(mappings.get(item.value.id, {}))
    return keywords


def _legacy_metadata_requirements(root: Path) -> list[str]:
    """Read install/test dependencies from legacy packaging metadata safely.

    This deliberately supports only static literals. Dynamic setup scripts can
    still provide a requirements file or a modern PEP 621 ``pyproject.toml``;
    executing arbitrary setup.py code during archive admission is not safe.
    """
    requirements: list[str] = []
    setup_cfg = root / "setup.cfg"
    if setup_cfg.is_file():
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(setup_cfg, encoding="utf-8")
        if parser.has_option("options", "install_requires"):
            requirements.extend(_split_requirement_block(parser.get("options", "install_requires")))
        if parser.has_section("options.extras_require"):
            for name, value in parser.items("options.extras_require"):
                requirements.extend(_selected_extra_requirements(name, value))

    setup_py = root / "setup.py"
    if setup_py.is_file():
        try:
            tree = ast.parse(setup_py.read_text(encoding="utf-8", errors="replace"))
            assignments = {
                statement.targets[0].id: statement.value
                for statement in tree.body
                if isinstance(statement, ast.Assign)
                and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)
            }
            keywords = _setup_keyword_values(tree, assignments)
            if keywords:
                if install_requires := keywords.get("install_requires"):
                    value = _literal_setup_value(install_requires, assignments)
                    if isinstance(value, str):
                        requirements.extend(_split_requirement_block(value))
                    elif isinstance(value, (list, tuple)):
                        requirements.extend(str(item).strip() for item in value if str(item).strip())
                if extras_require := keywords.get("extras_require"):
                    value = _literal_setup_value(extras_require, assignments)
                    if isinstance(value, dict):
                        for name, items in value.items():
                            requirements.extend(_selected_extra_requirements(str(name), items))
                if tests_require := keywords.get("tests_require"):
                    value = _literal_setup_value(tests_require, assignments)
                    if isinstance(value, str):
                        requirements.extend(_split_requirement_block(value))
                    elif isinstance(value, (list, tuple)):
                        requirements.extend(str(item).strip() for item in value if str(item).strip())
        except (OSError, SyntaxError, TypeError, ValueError):
            # Native requirement files and PEP 621 metadata remain authoritative.
            pass

    return list(dict.fromkeys(requirements))


def _write_legacy_metadata_requirements(root: Path, destination: Path) -> Path | None:
    requirements = _legacy_metadata_requirements(root)
    if not requirements:
        return None
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(requirements) + "\n", encoding="utf-8")
    return destination


def prepare_environment(
    specs: list[RuntimeProjectSpec],
    workspace: Path,
    *,
    timeout_seconds: int = 900,
    maximum_output_bytes: int = 10 * 1024 * 1024,
    expected_python: str | None = None,
    persistent_venv: Path | None = None,
    admission_command_timeout_seconds: int = ADMISSION_COMMAND_TIMEOUT_SECONDS,
) -> tuple[RuntimeResult, Path | None]:
    """Prepare one immutable project runtime.

    Project dependencies must never be resolved together.  Keeping this
    invariant at the lowest runtime layer prevents a caller from accidentally
    reintroducing a shared virtual environment even if it bypasses the API
    service, which already submits one project per preparation job.
    """
    result = RuntimeResult(status="runtime_failed")
    try:
        if len(specs) != 1:
            raise ValueError("Runtime preparation requires exactly one project")
        actual_python = f"{sys.version_info.major}.{sys.version_info.minor}"
        result.python_version = actual_python
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
        test_requirements: dict[str, list[Path]] = {}
        digest = hashlib.sha256(f"runtime-v{RUNTIME_PROTOCOL_VERSION}|python-{actual_python}".encode())
        for spec in sorted(specs, key=lambda item: item.project_id):
            digest.update(spec.project_id.encode())
            digest.update(spec.configured_source.encode())
            digest.update(spec.configured_tests.encode())
            digest.update(spec.archive.read_bytes())
            extracted = workspace / "projects" / spec.project_id
            safe_extract_zip(spec.archive, extracted)
            root = find_project_root(extracted).resolve()
            _validate_project_python(root, spec.project_id)
            source, test_dir = detect_layout(root, spec.configured_source, spec.configured_tests)
            test_dir = _runtime_test_directory(root, test_dir)
            dependency_files = [name for name in DEPENDENCY_FILES if (root / name).is_file()]
            roots[spec.project_id] = root
            sources[spec.project_id] = source
            tests[spec.project_id] = test_dir
            test_requirements[spec.project_id] = _test_requirement_files(root, test_dir)
            dependency_files.extend(path.relative_to(root).as_posix() for path in test_requirements[spec.project_id])
            result.projects[spec.project_id] = RuntimeProjectResult(
                project_root=str(root),
                source_directory=source.relative_to(root).as_posix() or ".",
                test_directory=test_dir.relative_to(root).as_posix() if test_dir.exists() else spec.configured_tests,
                dependency_files=dependency_files,
            )
        result.dependency_fingerprint = digest.hexdigest()
        result.runtime_digest = hashlib.sha256(
            json.dumps(
                {
                    "protocol": RUNTIME_PROTOCOL_VERSION,
                    "python": actual_python,
                    "project": result.dependency_fingerprint,
                    "tools": RUNTIME_TOOL_PACKAGES,
                },
                separators=(",", ":"),
                sort_keys=True,
            ).encode()
        ).hexdigest()

        venv_dir = (persistent_venv or workspace / ".venv").resolve()
        if venv_dir.exists():
            shutil.rmtree(venv_dir)
        deadline = time.monotonic() + timeout_seconds
        uv = shutil.which("uv")
        if uv:
            _run(
                result,
                "create project runtime",
                [uv, "venv", "--python", sys.executable, str(venv_dir)],
                workspace,
                deadline,
                maximum_output_bytes,
            )
        else:
            venv.EnvBuilder(with_pip=True, system_site_packages=True).create(venv_dir)
        python = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

        requirements: list[Path] = []
        dependency_groups: list[str] = []
        pyproject_requirements = False
        for project_id, root in roots.items():
            if (root / "pyproject.toml").is_file() and uv:
                if (root / "uv.lock").is_file():
                    exported = workspace / "resolved" / f"{project_id}.txt"
                    exported.parent.mkdir(parents=True, exist_ok=True)
                    _run(
                        result,
                        f"export {project_id} lock",
                        [
                            uv,
                            "export",
                            "--frozen",
                            "--all-groups",
                            "--no-emit-project",
                            "--format",
                            "requirements-txt",
                            "--output-file",
                            str(exported),
                        ],
                        root,
                        deadline,
                        maximum_output_bytes,
                    )
                    requirements.append(exported)
                else:
                    pyproject = root / "pyproject.toml"
                    requirements.append(pyproject)
                    pyproject_requirements = True
                    dependency_groups.extend(f"{pyproject}:{name}" for name in _dependency_group_names(pyproject))
            else:
                requirements.extend(root / name for name in LEGACY_REQUIREMENT_FILES if (root / name).is_file())
            legacy_metadata = _write_legacy_metadata_requirements(
                root,
                workspace / "resolved" / f"{project_id}-legacy-metadata.txt",
            )
            if legacy_metadata is not None:
                requirements.append(legacy_metadata)
            requirements.extend(test_requirements[project_id])

        if requirements or uv:
            command = (
                [uv, "pip", "install", "--python", str(python)]
                if uv
                else [str(python), "-m", "pip", "install", "--disable-pip-version-check"]
            )
            for requirement in requirements:
                command.extend(["-r", str(requirement)])
            if uv:
                if pyproject_requirements:
                    command.append("--all-extras")
                for group in dependency_groups:
                    command.extend(["--group", group])
                command.extend(RUNTIME_TOOL_PACKAGES)
            _run(
                result,
                "resolve project dependencies",
                command,
                workspace,
                deadline,
                maximum_output_bytes,
            )
            check = [uv, "pip", "check", "--python", str(python)] if uv else [str(python), "-m", "pip", "check"]
            _run(result, "verify dependency compatibility", check, workspace, deadline, maximum_output_bytes)
            result.install_strategy = "uv dependency-only project resolution" if uv else "pip project resolution"
        else:
            result.install_strategy = "PYTHONPATH (no dependency manifest)"

        site_packages = (
            venv_dir / "Lib" / "site-packages"
            if os.name == "nt"
            else venv_dir / "lib" / f"python{actual_python}" / "site-packages"
        )
        prepared_environment = dict(os.environ)
        prepared_environment["TESTGEN_PYTHON"] = str(python)
        import_roots = [source.parent if (source / "__init__.py").is_file() else source for source in sources.values()]
        prepared_environment["PYTHONPATH"] = os.pathsep.join(str(path) for path in import_roots)
        for project_id in roots:
            _, prepared_environment = prepare_project(
                roots[project_id],
                sources[project_id],
                prepared_environment,
                metadata_site=site_packages,
            )
        test_environment = {"PYTHONPATH": prepared_environment["PYTHONPATH"]}

        for project_id in roots:
            project_result = result.projects[project_id]
            pytest_target = tests[project_id]
            collect = _run(
                result,
                f"collect tests for {project_id}",
                [str(python), "-m", "pytest", "--collect-only", "-q", str(pytest_target)],
                roots[project_id],
                deadline,
                maximum_output_bytes,
                # Upstream collection is diagnostic. Generated PromptOpt tests
                # do not depend on every repository test module collecting.
                allowed_return_codes=(0, 1, 2, 3, 4, 5),
                pytest_plugin_autoload=bool(uv),
                extra_env=test_environment,
                timeout_seconds=admission_command_timeout_seconds,
                raise_on_timeout=False,
            )
            project_result.collected_tests = _parse_collected_tests(collect.output)
            coverage_data = workspace / "coverage" / f".coverage-{project_id}"
            coverage_json = workspace / "coverage" / f"{project_id}.json"
            coverage_json.parent.mkdir(parents=True, exist_ok=True)
            baseline: CommandResult | None = None
            collection_usable = not collect.timed_out and collect.return_code in (0, 1, 5)
            if collection_usable and 0 < project_result.collected_tests <= MAX_ADMISSION_BASELINE_TESTS:
                baseline = _run(
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
                    # Failing upstream assertions are diagnostic. Collection,
                    # internal and usage errors fall back to a zero baseline.
                    allowed_return_codes=(0, 1, 5),
                    pytest_plugin_autoload=bool(uv),
                    extra_env=test_environment,
                    timeout_seconds=admission_command_timeout_seconds,
                    raise_on_timeout=False,
                    raise_on_unexpected_exit=False,
                )

            if baseline is None or baseline.timed_out or baseline.return_code not in (0, 1, 5):
                coverage_data.unlink(missing_ok=True)
                empty_tests = roots[project_id] / ".promptopt-empty-tests"
                empty_tests.mkdir(parents=True, exist_ok=True)
                empty_config = empty_tests / "pytest.ini"
                empty_config.write_text("[pytest]\n", encoding="utf-8")
                _run(
                    result,
                    f"zero baseline for {project_id}",
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
                        "-c",
                        str(empty_config),
                        "-p",
                        "no:cacheprovider",
                        str(empty_tests),
                    ],
                    roots[project_id],
                    deadline,
                    maximum_output_bytes,
                    allowed_return_codes=(5,),
                    pytest_plugin_autoload=False,
                    extra_env=test_environment,
                    # Collection may intentionally use an aggressive timeout
                    # for arbitrary upstream suites.  The isolated empty-suite
                    # measurement still needs enough time to start the runtime
                    # and coverage.py, especially on Windows and cold workers.
                    timeout_seconds=max(10, admission_command_timeout_seconds),
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
    admission_command_timeout_seconds: int = ADMISSION_COMMAND_TIMEOUT_SECONDS,
) -> tuple[RuntimeResult, Path | None]:
    return prepare_environment(
        [RuntimeProjectSpec("project", archive, configured_source, configured_tests)],
        workspace,
        timeout_seconds=timeout_seconds,
        maximum_output_bytes=maximum_output_bytes,
        expected_python=expected_python,
        admission_command_timeout_seconds=admission_command_timeout_seconds,
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
    extra_env: dict[str, str] | None = None,
    timeout_seconds: float | None = None,
    raise_on_timeout: bool = True,
    raise_on_unexpected_exit: bool = True,
) -> CommandResult:
    remaining = max(1.0, deadline - time.monotonic())
    if timeout_seconds is not None:
        remaining = min(remaining, max(0.1, timeout_seconds))
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
    if extra_env:
        env.update(extra_env)
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
        existing_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = str(cwd / "src") + (os.pathsep + existing_pythonpath if existing_pythonpath else "")
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
    if item.timed_out and raise_on_timeout:
        raise RuntimeError(f"{name} timed out")
    if not item.timed_out and item.return_code not in allowed_return_codes and raise_on_unexpected_exit:
        detail = item.output[-2000:]
        if name == "resolve project dependencies":
            raise RuntimeError(f"Dependency conflict prevented this project runtime from being prepared: {detail}")
        raise RuntimeError(f"{name} failed with exit code {item.return_code}: {detail}")
    return item


def _parse_collected_tests(output: str) -> int:
    matches = re.findall(r"(\d+)\s+(?:tests?|items?)\s+collected", output)
    if matches:
        return int(matches[-1])
    return len(re.findall(r"::test[^\s]*", output))
