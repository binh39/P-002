from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, Field

from .models import PromptStatus


class ExperimentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    baseline_prompt: str = Field(min_length=1)
    module_path: str = Field(min_length=1)
    dataset_path: str = Field(min_length=1)
    source_root: str = Field(min_length=1)
    budget_limit: float = Field(default=5.0, gt=0)


class ExperimentOut(ExperimentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: PromptStatus
    error_message: str | None
    created_at: datetime.datetime


class CandidateCreate(BaseModel):
    prompt_text: str = Field(min_length=1)
    parent_id: str | None = None
    generation: int = Field(default=0, ge=0)
    fitness_score: float = Field(default=0.0, ge=0.0, le=1.0)
    pass_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    statement_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    branch_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    mutation_score: float = Field(default=0.0, ge=0.0, le=1.0)
    cost_usd: float = Field(default=0.0, ge=0.0)
    latency_seconds: float = Field(default=0.0, ge=0.0)


class CandidateOut(CandidateCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    experiment_id: str
    status: PromptStatus


class ReviewRequest(BaseModel):
    reviewer_id: str = Field(min_length=1, max_length=200)
    comment: str = Field(default="", max_length=5000)


class ApprovalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    candidate_id: str
    reviewer_id: str
    decision: str
    comment: str | None
    decided_at: datetime.datetime
