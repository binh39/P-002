from __future__ import annotations

import hashlib
import io
import json
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from coverage import Coverage

from backend.core.errors import AppError
from backend.modules.analysis.schemas import ProjectFunctionRecord

IGNORED_PARTS = {".git", ".venv", "venv", "site-packages", "__pycache__", "node_modules"}


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    functions: list[ProjectFunctionRecord]
    python_file_count: int
    statement_count: int
    branch_count: int
    warning_count: int


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
) -> AnalysisResult:
    try:
        bundle = zipfile.ZipFile(io.BytesIO(archive))
    except zipfile.BadZipFile as exc:
        raise AppError(422, "INVALID_ZIP", "The uploaded source archive is not a valid ZIP file") from exc

    candidates: list[zipfile.ZipInfo] = []
    total_size = 0
    for info in bundle.infolist():
        path = PurePosixPath(info.filename.replace("\\", "/"))
        if info.is_dir() or path.is_absolute() or ".." in path.parts:
            continue
        if path.suffix != ".py" or any(part in IGNORED_PARTS for part in path.parts):
            continue
        candidates.append(info)
        total_size += info.file_size
        if len(candidates) > max_python_files:
            raise AppError(413, "TOO_MANY_PYTHON_FILES", "The archive contains too many Python files")
        if total_size > max_uncompressed_bytes:
            raise AppError(413, "ANALYSIS_ARCHIVE_TOO_LARGE", "Python sources exceed the analysis limit")

    if not candidates:
        raise AppError(422, "NO_PYTHON_FILES", "The archive does not contain analyzable Python files")

    analyzed_at = datetime.now(UTC)
    warning_count = 0
    sources: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="prompt-optimizer-analysis-") as temporary:
        source_root = Path(temporary)
        for info in candidates:
            archive_path = PurePosixPath(info.filename.replace("\\", "/")).as_posix()
            try:
                source = bundle.read(info).decode("utf-8-sig")
                compile(source, archive_path, "exec")
            except (UnicodeDecodeError, SyntaxError):
                warning_count += 1
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

    return AnalysisResult(
        functions=functions,
        python_file_count=len(candidates),
        statement_count=statement_count,
        branch_count=branch_count,
        warning_count=warning_count,
    )
