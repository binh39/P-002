from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExperimentStatus(StrEnum):
    DRAFT = "draft"
    BASELINE_QUEUED = "baseline_queued"
    BASELINE_RUNNING = "baseline_running"
    BASELINE_SUCCEEDED = "baseline_succeeded"
    FAILED = "failed"


class CreateExperimentRequest(StrictModel):
    project_id: str
    name: str = Field(min_length=1, max_length=120)
    target_function_ids: list[str] = Field(min_length=1, max_length=50)


class ExperimentResponse(StrictModel):
    id: str
    project_id: str
    name: str
    target_function_ids: list[str]
    status: ExperimentStatus
    baseline_run_id: str | None = None
    created_at: datetime
    updated_at: datetime


class ExperimentRecord(ExperimentResponse):
    owner_id: str


class BaselineRunResponse(StrictModel):
    id: str
    experiment_id: str
    status: ExperimentStatus
    target_count: int
    coverage_score: float | None = None
    statement_coverage: float | None = None
    branch_coverage: float | None = None
    prompt_digest: str | None = None
    artifact_objects: dict[str, str] = Field(default_factory=dict)
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class BaselineRunRecord(BaselineRunResponse):
    pass


def new_id() -> str:
    return str(uuid4())
