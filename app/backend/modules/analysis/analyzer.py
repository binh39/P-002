from __future__ import annotations

import hashlib
import io
import json
import stat
import tempfile
import tomllib
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from coverage import Coverage
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import Version

from backend.core.errors import AppError
from backend.modules.analysis.schemas import ProjectFunctionRecord

IGNORED_PARTS = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "site-packages",
    "venv",
}
NON_TARGET_PARTS = {"tests", "test", "migrations"}
MAX_ARCHIVE_ENTRIES = 50_000
SUPPORTED_PYTHON_MINORS = ("3.10", "3.11", "3.12", "3.13")
MAX_PROJECT_METADATA_BYTES = 1_000_000


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    functions: list[ProjectFunctionRecord]
    python_file_count: int
    statement_count: int
    branch_count: int
    warning_count: int
    python_version: str | None = None
    requires_python: str | None = None
    warnings: tuple[str, ...] = ()


def _project_python_requirement(
    bundle: zipfile.ZipFile,
    entries: list[zipfile.ZipInfo],
    root_prefix: str,
) -> str | None:
    """Read root pyproject metadata without extracting or importing project code."""
    pyproject = next(
        (
            info
            for info in entries
            if not info.is_dir()
            and _project_relative_path(PurePosixPath(info.filename.replace("\\", "/")), root_prefix).as_posix()
            == "pyproject.toml"
        ),
        None,
    )
    if pyproject is None:
        return None
    if pyproject.file_size > MAX_PROJECT_METADATA_BYTES:
        raise AppError(422, "PROJECT_METADATA_TOO_LARGE", "pyproject.toml is too large to inspect safely")
    try:
        payload = tomllib.loads(bundle.read(pyproject).decode("utf-8-sig"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError, RuntimeError, zipfile.BadZipFile) as exc:
        raise AppError(422, "INVALID_PYPROJECT", "pyproject.toml is not valid UTF-8 TOML") from exc
    project = payload.get("project")
    requirement = project.get("requires-python") if isinstance(project, dict) else None
    if requirement is None:
        return None
    if not isinstance(requirement, str) or not requirement.strip():
        raise AppError(422, "INVALID_PYTHON_REQUIREMENT", "[project].requires-python must be a non-empty string")
    return requirement.strip()


def _compatible_python_minor(requirement: str | None, preferred: str) -> str | None:
    if requirement is None:
        return preferred
    try:
        supported = SpecifierSet(requirement)
    except InvalidSpecifier as exc:
        raise AppError(
            422,
            "INVALID_PYTHON_REQUIREMENT",
            f"[project].requires-python is invalid: {requirement!r}",
        ) from exc

    ordered = [preferred, *(version for version in SUPPORTED_PYTHON_MINORS if version != preferred)]
    for minor in ordered:
        # The exact patch installed in the immutable worker can change while
        # the routing contract remains Python-minor based. These endpoints
        # establish whether the requirement admits any normal patch in it.
        if any(Version(f"{minor}.{patch}") in supported for patch in (0, 999)):
            return minor
    raise AppError(
        422,
        "PYTHON_RUNTIME_UNAVAILABLE",
        f"Project requires Python {requirement}, but available isolated runtimes are "
        f"{', '.join(SUPPORTED_PYTHON_MINORS)}",
    )


def _coverage_report(source_files: list[Path], output: Path) -> dict:
    """Build a static function-level coverage.py report without importing user code."""
    coverage = Coverage(data_file=None, branch=True)
    coverage.set_option("run:disable_warnings", ["no-data-collected"])
    coverage.start()
    coverage.stop()
    coverage.json_report(morfs=[str(path) for path in source_files], outfile=str(output))
    with output.open(encoding="utf-8") as report_file:
        return json.load(report_file)


def _report_file_by_archive_path(report: dict, archive_paths: list[str]) -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    for report_name, file_data in report.get("files", {}).items():
        normalized = report_name.replace("\\", "/").lower()
        matches = [
            archive_path
            for archive_path in archive_paths
            if normalized == archive_path.lower() or normalized.endswith("/" + archive_path.lower())
        ]
        if len(matches) == 1:
            indexed[matches[0]] = file_data
    return indexed


def _function_end_line(function_data: dict, source_line_count: int) -> int:
    lines = [int(function_data.get("start_line", 1))]
    for key in ("executed_lines", "missing_lines", "excluded_lines"):
        lines.extend(int(line) for line in function_data.get(key, []))
    for key in ("executed_branches", "missing_branches"):
        lines.extend(int(line) for arc in function_data.get(key, []) for line in arc if int(line) > 0)
    return min(max(lines), source_line_count)


def _class_name(qualified_name: str, classes: dict) -> str:
    candidates = [name for name in classes if name and qualified_name.startswith(name + ".")]
    return max(candidates, key=len, default="")


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    return stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK


def _is_python_target(path: PurePosixPath) -> bool:
    lowered_parts = {part.lower() for part in path.parts}
    filename = path.name.lower()
    return (
        path.suffix.lower() == ".py"
        and not lowered_parts.intersection(IGNORED_PARTS | NON_TARGET_PARTS)
        and not filename.startswith("test_")
        and not filename.endswith("_test.py")
    )


def _archive_root_prefix(entries: list[zipfile.ZipInfo]) -> str:
    """Mirror the runtime's single-wrapper-directory project-root detection."""
    children: set[str] = set()
    safe_entries: list[tuple[zipfile.ZipInfo, PurePosixPath]] = []
    for info in entries:
        path = PurePosixPath(info.filename.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts or not path.parts:
            continue
        if path.parts[0] in {"__MACOSX", ".git"}:
            continue
        children.add(path.parts[0])
        safe_entries.append((info, path))
    if len(children) != 1:
        return ""
    prefix = next(iter(children))
    # A lone root-level file is not a wrapper directory.
    if any(len(path.parts) == 1 and not info.is_dir() for info, path in safe_entries):
        return ""
    return prefix


def _project_relative_path(path: PurePosixPath, root_prefix: str) -> PurePosixPath:
    if root_prefix and path.parts and path.parts[0] == root_prefix:
        return PurePosixPath(*path.parts[1:])
    return path


def _records_from_report(
    project_id: str,
    sources: dict[str, str],
    report: dict,
    analyzed_at: datetime,
) -> list[ProjectFunctionRecord]:
    records: list[ProjectFunctionRecord] = []
    report_files = _report_file_by_archive_path(report, list(sources))
    for archive_path, source in sources.items():
        file_data = report_files.get(archive_path)
        if file_data is None:
            continue
        source_lines = source.splitlines()
        classes = file_data.get("classes", {})
        for qualified_name, function_data in file_data.get("functions", {}).items():
            if not qualified_name:
                continue
            summary = function_data.get("summary", {})
            num_statements = int(summary.get("num_statements", 0))
            num_branches = int(summary.get("num_branches", 0))
            # This is the same denominator validity required by GEPA preflight.
            if num_statements <= 0 or num_branches < 0:
                continue
            start_line = int(function_data.get("start_line", 1))
            end_line = _function_end_line(function_data, len(source_lines))
            name = qualified_name.rsplit(".", 1)[-1]
            if not name.isidentifier():
                continue
            function_id = hashlib.sha256(f"{archive_path}:{qualified_name}:{start_line}".encode()).hexdigest()[:24]
            records.append(
                ProjectFunctionRecord(
                    id=function_id,
                    project_id=project_id,
                    file=archive_path,
                    class_name=_class_name(qualified_name, classes),
                    name=name,
                    qualified_name=qualified_name,
                    start_line=start_line,
                    end_line=end_line,
                    loc=end_line - start_line + 1,
                    statements=num_statements,
                    branches=num_branches,
                    status="Valid",
                    source="\n".join(source_lines[start_line - 1 : end_line]),
                    analyzed_at=analyzed_at,
                )
            )
    return records


def analyze_zip(
    project_id: str,
    archive: bytes,
    max_python_files: int,
    max_uncompressed_bytes: int,
    preferred_python_version: str = "3.12",
) -> AnalysisResult:
    try:
        bundle = zipfile.ZipFile(io.BytesIO(archive))
    except zipfile.BadZipFile as exc:
        raise AppError(422, "INVALID_ZIP", "The uploaded source archive is not a valid ZIP file") from exc

    entries = bundle.infolist()
    if len(entries) > MAX_ARCHIVE_ENTRIES:
        bundle.close()
        raise AppError(413, "TOO_MANY_ARCHIVE_ENTRIES", "The archive contains too many entries")

    root_prefix = _archive_root_prefix(entries)
    requires_python = _project_python_requirement(bundle, entries, root_prefix)
    python_version = _compatible_python_minor(requires_python, preferred_python_version)
    candidates: list[tuple[zipfile.ZipInfo, str]] = []
    normalized_paths: set[str] = set()
    total_size = 0
    skipped_symlinks = 0
    for info in entries:
        path = PurePosixPath(info.filename.replace("\\", "/"))
        if info.is_dir() or path.is_absolute() or ".." in path.parts:
            continue
        if _is_symlink(info):
            # Source archives downloaded from Git hosts commonly preserve
            # repository symlinks. Never follow or extract them, but do not
            # reject the otherwise valid project either.
            skipped_symlinks += 1
            continue
        if info.flag_bits & 0x1:
            bundle.close()
            raise AppError(422, "ENCRYPTED_ZIP_ENTRY", "Encrypted ZIP entries are not supported")
        project_path = _project_relative_path(path, root_prefix)
        if not _is_python_target(project_path):
            continue
        archive_path = project_path.as_posix()
        normalized = archive_path.casefold()
        if normalized in normalized_paths:
            bundle.close()
            raise AppError(422, "DUPLICATE_ZIP_ENTRY", "The archive contains duplicate Python paths")
        normalized_paths.add(normalized)
        candidates.append((info, archive_path))
        total_size += info.file_size
        if len(candidates) > max_python_files:
            bundle.close()
            raise AppError(413, "TOO_MANY_PYTHON_FILES", "The archive contains too many Python files")
        if total_size > max_uncompressed_bytes:
            bundle.close()
            raise AppError(413, "ANALYSIS_ARCHIVE_TOO_LARGE", "Python sources exceed the analysis limit")

    if not candidates:
        bundle.close()
        raise AppError(422, "NO_PYTHON_FILES", "The archive does not contain analyzable Python files")

    analyzed_at = datetime.now(UTC)
    warnings = (
        [f"Skipped {skipped_symlinks} symbolic link(s); archive links are never extracted."] if skipped_symlinks else []
    )
    sources: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="prompt-optimizer-analysis-") as temporary:
        source_root = Path(temporary)
        for info, archive_path in candidates:
            try:
                source = bundle.read(info).decode("utf-8-sig")
                compile(source, archive_path, "exec")
            except (UnicodeDecodeError, SyntaxError, RuntimeError, NotImplementedError, zipfile.BadZipFile) as exc:
                warnings.append(f"Skipped {archive_path}: {type(exc).__name__}: {exc}")
                continue
            destination = source_root.joinpath(*PurePosixPath(archive_path).parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(source, encoding="utf-8")
            sources[archive_path] = source

        if sources:
            report = _coverage_report(
                [source_root.joinpath(*PurePosixPath(path).parts) for path in sources],
                source_root / "coverage.json",
            )
            functions = _records_from_report(project_id, sources, report, analyzed_at)
            totals = report.get("totals", {})
            statement_count = int(totals.get("num_statements", 0))
            branch_count = int(totals.get("num_branches", 0))
        else:
            functions = []
            statement_count = 0
            branch_count = 0

    bundle.close()

    return AnalysisResult(
        functions=functions,
        python_file_count=len(candidates),
        statement_count=statement_count,
        branch_count=branch_count,
        warning_count=len(warnings),
        python_version=python_version,
        requires_python=requires_python,
        warnings=tuple(warnings),
    )
