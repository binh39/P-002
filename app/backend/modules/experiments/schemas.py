from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

SUPPORTED_MODELS = (
    "vertex_ai/gemini-2.5-flash",
    "vertex_ai/gemini-2.5-flash-lite",
    "vertex_ai/gemini-2.5-pro",
    "vertex_ai/gemini-3.1-flash-lite",
    "vertex_ai/gemini-3.1-pro-preview",
    "vertex_ai/gemini-3.5-flash",
    "vertex_ai/gemini-3.5-flash-lite",
    "vertex_ai/gemini-3.6-flash",
    "openai/gpt-4.1-mini",
    "openai/gpt-4.1",
    "openai/gpt-5-mini",
    "openai/gpt-5",
    "deepseek/deepseek-chat",
    "deepseek/deepseek-reasoner",
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExperimentStatus(StrEnum):
    DRAFT = "draft"
    BASELINE_QUEUED = "baseline_queued"
    BASELINE_RUNNING = "baseline_running"
    BASELINE_SUCCEEDED = "baseline_succeeded"
    OPTIMIZATION_QUEUED = "optimization_queued"
    OPTIMIZING = "optimizing"
    CANDIDATE_EVALUATING = "candidate_evaluating"
    OPTIMIZATION_SUCCEEDED = "optimization_succeeded"
    COMPARISON_QUEUED = "comparison_queued"
    COMPARING = "comparing"
    COMPARISON_SUCCEEDED = "comparison_succeeded"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"
    FAILED = "failed"


class SamplingMethod(StrEnum):
    RANDOM = "random"
    MOST_BRANCHES = "most_branches"
    MOST_STATEMENTS = "most_statements"
    MANUAL = "manual"


class DatasetPercentages(StrictModel):
    train: int = Field(default=20, ge=0, le=100)
    validation: int = Field(default=40, ge=0, le=100)
    test: int = Field(default=40, gt=0, le=100)

    @model_validator(mode="after")
    def total_is_one_hundred(self):
        if self.train + self.validation + self.test != 100:
            raise ValueError("Dataset percentages must total 100")
        return self


class ExperimentSettings(StrictModel):
    coverup_model: str = "vertex_ai/gemini-3.6-flash"
    optimize_model: str = "vertex_ai/gemini-3.6-flash"
    max_attempts: int = Field(default=3, ge=1, le=20)
    repeat_tests: int = Field(default=5, ge=0, le=20)
    max_concurrency: int = Field(default=10, ge=1, le=32)
    rate_limit: int | None = Field(default=None, ge=1)
    pytest_args: str = Field(default="", max_length=500)
    max_metric_calls: int = Field(default=30, ge=3)
    evaluation_replicates: int = Field(default=1, ge=1, le=10)
    reflection_temperature: float = Field(default=0.7, ge=0, le=2)

    @model_validator(mode="after")
    def models_are_supported(self):
        if self.coverup_model not in SUPPORTED_MODELS:
            raise ValueError("Unsupported COVERUP_MODEL")
        if self.optimize_model not in SUPPORTED_MODELS:
            raise ValueError("Unsupported OPTIMIZE_MODEL")
        return self


class BaselinePromptInput(StrictModel):
    initial: str = Field(min_length=1, max_length=32 * 1024)
    error: str = Field(min_length=1, max_length=32 * 1024)


class TargetReference(StrictModel):
    project_id: str
    function_id: str
    project: str
    source_file: str
    symbol: str
    statements: int = 0
    branches: int = 0
    loc: int = 0

    @property
    def key(self) -> str:
        return f"{self.project_id}::{self.function_id}"


class ProjectSnapshot(StrictModel):
    project_id: str
    name: str
    commit: str | None = None
    source_directory: str
    test_directory: str
    runner_project: str


class CreateExperimentRequest(StrictModel):
    project_ids: list[str] = Field(min_length=1)
    name: str = Field(min_length=1, max_length=120)
    sampling_method: SamplingMethod = SamplingMethod.RANDOM
    max_targets: int | None = Field(default=None, ge=3)
    random_seed: int = Field(default=7, ge=0)
    split_percentages: DatasetPercentages = Field(default_factory=DatasetPercentages)
    manual_splits: dict[str, list[str]] | None = None
    settings: ExperimentSettings = Field(default_factory=ExperimentSettings)
    baseline_prompt: BaselinePromptInput | None = None

    @model_validator(mode="after")
    def validate_selection(self):
        if len(self.project_ids) != len(set(self.project_ids)):
            raise ValueError("Duplicate project IDs are not allowed")
        if self.sampling_method == SamplingMethod.MANUAL and not self.manual_splits:
            raise ValueError("Manual sampling requires explicit dataset splits")
        if self.sampling_method != SamplingMethod.MANUAL and self.manual_splits is not None:
            raise ValueError("Manual splits are only valid with manual sampling")
        return self


class ExperimentResponse(StrictModel):
    id: str
    project_id: str = ""  # Kept while old clients/documents are migrated.
    project_ids: list[str] = Field(default_factory=list)
    project_snapshots: list[ProjectSnapshot] = Field(default_factory=list)
    name: str
    target_function_ids: list[str] = Field(default_factory=list)
    targets: list[TargetReference] = Field(default_factory=list)
    sampling_method: SamplingMethod = SamplingMethod.RANDOM
    max_targets: int | None = None
    dataset_splits: dict[str, list[str]] = Field(default_factory=dict)
    split_percentages: DatasetPercentages = Field(default_factory=DatasetPercentages)
    split_seed: int = 7
    settings: ExperimentSettings = Field(default_factory=ExperimentSettings)
    baseline_prompt: dict[str, str] | None = None
    optimization_eligible: bool = False
    status: ExperimentStatus
    baseline_run_id: str | None = None
    optimization_run_id: str | None = None
    comparison_run_id: str | None = None
    prompt_version_id: str | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def migrate_legacy_identity(self):
        if not self.project_ids and self.project_id:
            self.project_ids = [self.project_id]
        if not self.project_id and self.project_ids:
            self.project_id = self.project_ids[0]
        return self


class ExperimentRecord(ExperimentResponse):
    owner_id: str


class ExperimentListResponse(StrictModel):
    items: list[ExperimentResponse]
    total: int


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
    target_metrics: dict[str, dict] = Field(default_factory=dict)
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class BaselineRunRecord(BaselineRunResponse):
    pass


class OptimizationRunResponse(StrictModel):
    id: str
    experiment_id: str
    status: ExperimentStatus
    parent_prompt_digest: str
    candidate_prompt: dict[str, str] | None = None
    candidate_prompt_digest: str | None = None
    baseline_validation_score: float | None = None
    candidate_validation_score: float | None = None
    candidate_count: int = 0
    metric_calls: int = 0
    final_validation: dict = Field(default_factory=dict)
    artifact_objects: dict[str, str] = Field(default_factory=dict)
    cloud_artifact_prefix: str | None = None
    cloud_deadline_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class OptimizationRunRecord(OptimizationRunResponse):
    # Internal routing metadata. This is persisted with the run but intentionally
    # omitted from OptimizationRunResponse so clients cannot choose a billing project.
    vertexai_project: str | None = None


class EvolutionIteration(StrictModel):
    iteration: int
    strategy: str
    parent_program: str | None = None
    parent_validation_score: float | None = None
    component: str | None = None
    proposed_prompt: str | None = None
    parent_minibatch_sum: float | None = None
    candidate_minibatch_sum: float | None = None
    decision: str
    full_validation: bool = False
    best_statement: float | None = None
    best_branch: float | None = None
    best_score: float | None = None
    best_candidate_changed: bool = False
    # Retained so persisted evolution snapshots from earlier releases still validate.
    pareto_changed: bool = False


class EvolutionMetricPoint(StrictModel):
    iteration: int
    statement: float | None = None
    branch: float | None = None
    score: float | None = None


class EvolutionResponse(StrictModel):
    available: bool
    source: str = "cloud_run_stdout"
    message: str = ""
    iterations: list[EvolutionIteration] = Field(default_factory=list)
    metrics: list[EvolutionMetricPoint] = Field(default_factory=list)


class ComparisonRunResponse(StrictModel):
    id: str
    experiment_id: str
    optimization_run_id: str
    status: ExperimentStatus
    baseline_prompt_digest: str
    candidate_prompt_digest: str
    test_target_ids: list[str]
    replicate_count: int
    baseline_metrics: dict = Field(default_factory=dict)
    candidate_metrics: dict = Field(default_factory=dict)
    absolute_gain: float | None = None
    relative_gain: float | None = None
    promotion_eligible: bool = False
    decision_reason: str = ""
    artifact_objects: dict[str, str] = Field(default_factory=dict)
    prompt_version_id: str | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ComparisonRunRecord(ComparisonRunResponse):
    pass


class PromptVersionStatus(StrEnum):
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class PromptVersionResponse(StrictModel):
    id: str
    experiment_id: str
    comparison_run_id: str
    parent_prompt_digest: str
    prompt_digest: str
    prompt: dict[str, str]
    status: PromptVersionStatus
    reviewer_id: str | None = None
    review_comment: str = ""
    reviewed_at: datetime | None = None
    created_at: datetime


class PromptVersionListResponse(StrictModel):
    items: list[PromptVersionResponse]
    total: int
    offset: int
    limit: int


class PromptVersionRecord(PromptVersionResponse):
    pass


class ReviewPromptVersionRequest(StrictModel):
    comment: str = Field(default="", max_length=1000)


def new_id() -> str:
    return str(uuid4())
