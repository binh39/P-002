from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

PREPARED_RUNTIME_PROTOCOL_VERSION = 11
MINIMUM_RUNTIME_PROTOCOL_VERSION = 13
RUNTIME_EXECUTION_MODE_GENERIC = "generic_worker_bundle"
RUNTIME_EXECUTION_MODE_PROJECT_IMAGE = "project_image"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectStatus(StrEnum):
    UPLOADED = "uploaded"
    ANALYZING = "analyzing"
    READY = "ready"
    WARNING = "warning"
    FAILED = "failed"


class RuntimeStatus(StrEnum):
    NOT_REQUESTED = "not_requested"
    QUEUED = "runtime_queued"
    PREPARING = "runtime_preparing"
    READY = "runtime_ready"
    FAILED = "runtime_failed"


class RuntimeProjectReport(StrictModel):
    source_directory: str = ""
    test_directory: str = ""
    dependency_files: list[str] = Field(default_factory=list)
    collected_tests: int = 0
    statement_coverage: float | None = None
    branch_coverage: float | None = None


class RuntimeReport(StrictModel):
    status: RuntimeStatus
    source_directory: str = ""
    test_directory: str = ""
    dependency_files: list[str] = Field(default_factory=list)
    install_strategy: str = ""
    collected_tests: int = 0
    statement_coverage: float | None = None
    branch_coverage: float | None = None
    commands: list[dict] = Field(default_factory=list)
    projects: dict[str, RuntimeProjectReport] = Field(default_factory=dict)
    dependency_fingerprint: str | None = None
    runtime_digest: str | None = None
    python_version: str | None = None
    runtime_image: str | None = None
    runtime_worker_job: str | None = None
    source_archive_sha256: str | None = None
    source_archive_object: str | None = None
    runtime_bundle_sha256: str | None = None
    bundle_object: str | None = None
    error: str | None = None
    protocol_version: int = 1
    execution_mode: str = RUNTIME_EXECUTION_MODE_GENERIC


class RuntimeSettings(StrictModel):
    python_version: str = Field(default="3.12", pattern=r"^3\.(10|11|12|13)$")
    runtime_image: str = Field(default="promptopt-runtime-preparer", max_length=200)
    working_directory: str = Field(default="./", max_length=300)
    source_directory: str = Field(default="src", max_length=300)
    cpu: int = Field(default=1, ge=1, le=8)
    memory_mb: int = Field(default=2048, ge=512, le=32768)
    run_timeout_seconds: int = Field(default=900, ge=30, le=7200)
    maximum_workers: int = Field(default=4, ge=1, le=32)


class DependencySettings(StrictModel):
    install_command: str = Field(default="pip install -r requirements.txt", max_length=1000)
    requirements_file: str = Field(default="requirements.txt", max_length=300)
    lock_file: str | None = Field(default=None, max_length=300)
    cache_dependencies: bool = True
    extra_package_index: str | None = Field(default=None, max_length=500)


class TestSettings(StrictModel):
    framework: str = Field(default="pytest", pattern=r"^(pytest|unittest)$")
    test_directory: str = Field(default="tests", max_length=300)
    test_command: str = Field(default="pytest -q", max_length=1000)
    test_pattern: str = Field(default="test_*.py", max_length=100)
    per_test_timeout_seconds: int = Field(default=30, ge=1, le=1800)
    retry_count: int = Field(default=0, ge=0, le=5)


class CoverageSettings(StrictModel):
    statement_enabled: bool = True
    branch_enabled: bool = True
    config_file: str | None = Field(default=".coveragerc", max_length=300)
    include_pattern: str = Field(default="src/**/*.py", max_length=500)
    omit_pattern: str = Field(default="*/tests/*,*/migrations/*", max_length=500)
    source_package: str = Field(default="src", max_length=300)


class SecuritySettings(StrictModel):
    network_access: bool = False
    read_only_source: bool = True
    allowed_environment_variables: list[str] = Field(default_factory=lambda: ["PYTHONHASHSEED", "TZ"], max_length=30)
    maximum_output_bytes: int = Field(default=10 * 1024 * 1024, ge=1024, le=100 * 1024 * 1024)


class ProjectSettings(StrictModel):
    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)
    dependencies: DependencySettings = Field(default_factory=DependencySettings)
    tests: TestSettings = Field(default_factory=TestSettings)
    coverage: CoverageSettings = Field(default_factory=CoverageSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)


class RuntimeSettingsPatch(StrictModel):
    python_version: str | None = Field(default=None, pattern=r"^3\.(10|11|12|13)$")
    runtime_image: str | None = Field(default=None, max_length=200)
    working_directory: str | None = Field(default=None, max_length=300)
    source_directory: str | None = Field(default=None, max_length=300)
    cpu: int | None = Field(default=None, ge=1, le=8)
    memory_mb: int | None = Field(default=None, ge=512, le=32768)
    run_timeout_seconds: int | None = Field(default=None, ge=30, le=7200)
    maximum_workers: int | None = Field(default=None, ge=1, le=32)


class DependencySettingsPatch(StrictModel):
    install_command: str | None = Field(default=None, max_length=1000)
    requirements_file: str | None = Field(default=None, max_length=300)
    lock_file: str | None = Field(default=None, max_length=300)
    cache_dependencies: bool | None = None
    extra_package_index: str | None = Field(default=None, max_length=500)


class TestSettingsPatch(StrictModel):
    framework: str | None = Field(default=None, pattern=r"^(pytest|unittest)$")
    test_directory: str | None = Field(default=None, max_length=300)
    test_command: str | None = Field(default=None, max_length=1000)
    test_pattern: str | None = Field(default=None, max_length=100)
    per_test_timeout_seconds: int | None = Field(default=None, ge=1, le=1800)
    retry_count: int | None = Field(default=None, ge=0, le=5)


class CoverageSettingsPatch(StrictModel):
    statement_enabled: bool | None = None
    branch_enabled: bool | None = None
    config_file: str | None = Field(default=None, max_length=300)
    include_pattern: str | None = Field(default=None, max_length=500)
    omit_pattern: str | None = Field(default=None, max_length=500)
    source_package: str | None = Field(default=None, max_length=300)


class SecuritySettingsPatch(StrictModel):
    network_access: bool | None = None
    read_only_source: bool | None = None
    allowed_environment_variables: list[str] | None = Field(default=None, max_length=30)
    maximum_output_bytes: int | None = Field(default=None, ge=1024, le=100 * 1024 * 1024)


class ProjectSettingsPatch(StrictModel):
    runtime: RuntimeSettingsPatch | None = None
    dependencies: DependencySettingsPatch | None = None
    tests: TestSettingsPatch | None = None
    coverage: CoverageSettingsPatch | None = None
    security: SecuritySettingsPatch | None = None


class CreateProjectRequest(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    upload_id: str
    branch: str = Field(default="main", min_length=1, max_length=200)
    commit: str | None = Field(default=None, max_length=64)
    runtime_environment_id: str | None = Field(default=None, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    runtime_environment_name: str | None = Field(default=None, min_length=1, max_length=100)
    settings: ProjectSettings = Field(default_factory=ProjectSettings)


class ProjectResponse(StrictModel):
    id: str
    name: str
    description: str
    upload_id: str
    object_name: str
    branch: str
    commit: str | None
    status: ProjectStatus
    settings: ProjectSettings
    python_file_count: int = 0
    function_count: int = 0
    statement_count: int = 0
    branch_count: int = 0
    analyzed_at: datetime | None = None
    analysis_error: str | None = None
    runtime_environment_id: str | None = None
    runtime_environment_name: str | None = None
    runtime_bundle_object: str | None = None
    runtime_dependency_fingerprint: str | None = None
    runtime_digest: str | None = None
    runtime_image: str | None = None
    runtime_worker_job: str | None = None
    runtime_execution_mode: str | None = None
    source_archive_sha256: str | None = None
    runtime_source_archive_object: str | None = None
    runtime_bundle_sha256: str | None = None
    runtime_status: RuntimeStatus = RuntimeStatus.NOT_REQUESTED
    runtime_report: RuntimeReport | None = None
    runtime_artifact_prefix: str | None = None
    runtime_factory_prefix: str | None = None
    runtime_started_at: datetime | None = None
    runtime_finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ProjectRecord(ProjectResponse):
    owner_id: str


class ProjectListResponse(StrictModel):
    items: list[ProjectResponse]
    total: int
