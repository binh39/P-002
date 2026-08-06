import ast
import hashlib
import io
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePosixPath

from src.core.errors import AppError
from src.modules.analysis.schemas import ProjectFunctionRecord

IGNORED_PARTS = {".git", ".venv", "venv", "site-packages", "__pycache__", "node_modules"}


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    functions: list[ProjectFunctionRecord]
    python_file_count: int
    statement_count: int
    branch_count: int
    warning_count: int


class FunctionVisitor(ast.NodeVisitor):
    def __init__(self, project_id: str, path: str, source: str, analyzed_at: datetime):
        self.project_id = project_id
        self.path = path
        self.source = source
        self.lines = source.splitlines()
        self.analyzed_at = analyzed_at
        self.class_stack: list[str] = []
        self.function_stack: list[str] = []
        self.functions: list[ProjectFunctionRecord] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        qualified_parts = [*self.class_stack, *self.function_stack, node.name]
        qualified_name = ".".join(qualified_parts)
        end_line = node.end_lineno or node.lineno
        body_nodes = list(ast.walk(node))
        statements = sum(isinstance(item, ast.stmt) for item in body_nodes)
        branches = sum(
            isinstance(item, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.IfExp)) for item in body_nodes
        ) + sum(len(item.handlers) for item in body_nodes if isinstance(item, ast.Try))
        function_id = hashlib.sha256(f"{self.path}:{qualified_name}:{node.lineno}".encode()).hexdigest()[:24]
        self.functions.append(
            ProjectFunctionRecord(
                id=function_id,
                project_id=self.project_id,
                file=self.path,
                class_name=".".join(self.class_stack),
                name=node.name,
                qualified_name=qualified_name,
                start_line=node.lineno,
                end_line=end_line,
                loc=end_line - node.lineno + 1,
                statements=statements,
                branches=branches,
                status="Valid",
                source="\n".join(self.lines[node.lineno - 1 : end_line]),
                analyzed_at=self.analyzed_at,
            )
        )
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()


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

    analyzed_at = datetime.now(UTC)
    if not candidates:
        raise AppError(422, "NO_PYTHON_FILES", "The archive does not contain analyzable Python files")
    functions: list[ProjectFunctionRecord] = []
    statement_count = 0
    branch_count = 0
    warning_count = 0
    for info in candidates:
        path = PurePosixPath(info.filename.replace("\\", "/")).as_posix()
        try:
            source = bundle.read(info).decode("utf-8-sig")
            tree = ast.parse(source, filename=path)
        except (UnicodeDecodeError, SyntaxError):
            warning_count += 1
            continue
        visitor = FunctionVisitor(project_id, path, source, analyzed_at)
        visitor.visit(tree)
        functions.extend(visitor.functions)
        statement_count += sum(isinstance(node, ast.stmt) for node in ast.walk(tree))
        branch_count += sum(
            isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.IfExp)) for node in ast.walk(tree)
        ) + sum(len(node.handlers) for node in ast.walk(tree) if isinstance(node, ast.Try))

    return AnalysisResult(
        functions=functions,
        python_file_count=len(candidates),
        statement_count=statement_count,
        branch_count=branch_count,
        warning_count=warning_count,
    )
