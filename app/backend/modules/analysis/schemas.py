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
