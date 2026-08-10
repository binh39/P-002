from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CoveragePoint(StrictModel):
    day: str
    branch: float
    statement: float


class DashboardKpi(StrictModel):
    label: str
    value: str
    delta: str
    trend: Literal["up", "down", "neutral"]
    icon: Literal["experiments", "running", "branch", "statement"]


class DashboardExperiment(StrictModel):
    id: str
    name: str
    model: str
    branch_coverage: float = 0
    statement_coverage: float = 0
    status: Literal["completed", "running", "pending", "failed"]
    updated_at: str


class QuickStat(StrictModel):
    label: str
    value: str


class DashboardResponse(StrictModel):
    project_name: str
    as_of: str
    coverage: list[CoveragePoint] = Field(default_factory=list)
    kpis: list[DashboardKpi] = Field(default_factory=list)
    quick_stats: list[QuickStat] = Field(default_factory=list)
    experiments: list[DashboardExperiment] = Field(default_factory=list)
