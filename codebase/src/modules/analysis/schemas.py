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
