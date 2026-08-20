from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectFunctionRecord(StrictModel):
    id: str
    project_id: str
    file: str
    class_name: str = ""
    name: str
    qualified_name: str
    start_line: int
    end_line: int
    loc: int
    statements: int
    branches: int
    status: str
    source: str
    analyzed_at: datetime


class ProjectFunctionResponse(StrictModel):
    id: str
    project_id: str
    file: str
    class_name: str
    name: str
    qualified_name: str
    start_line: int
    end_line: int
    loc: int
    statements: int
    branches: int
    status: str


class ProjectFunctionListResponse(StrictModel):
    items: list[ProjectFunctionResponse]
    total: int


class FunctionSourceResponse(StrictModel):
    source: str


def is_valid_optimization_function(function: ProjectFunctionRecord) -> bool:
    """Match the optimizer's current coverage-denominator validity rule."""
    return function.status == "Valid" and function.statements > 0 and function.branches >= 0


def normalize_optimization_source_file(source_directory: str, source_file: str) -> str | None:
    """Return a project-relative runner path only when it belongs to the coverage source."""
    source = source_directory.replace("\\", "/").strip("/")
    normalized = source_file.replace("\\", "/").lstrip("./")
    if source in {"", "."}:
        return normalized
    if normalized == source or normalized.startswith(f"{source}/"):
        return normalized
    # Analysis records from an older protocol may retain the archive wrapper
    # directory (for example repo-main/src/pkg.py).
    marker = f"/{source}/"
    if marker in f"/{normalized}":
        suffix = f"/{normalized}".split(marker, 1)[1]
        return f"{source}/{suffix}"
    return None
