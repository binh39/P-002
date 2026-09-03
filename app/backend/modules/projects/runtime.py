import asyncio
import json
import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import uuid4

from cloud.sandbox_security import bounded_redacted_text

from backend.core.errors import AppError
from backend.infrastructure.storage import ObjectStorage

from .repository import ProjectRepository
from .rollout import parse_runtime_report
from .schemas import (
    BuildStatus,
    DependencyConflict,
    ExecutionStatus,
    FailureStage,
    ProjectRecord,
    ProjectResponse,
    RuntimeProjectReport,
    RuntimeReport,
    RuntimeStatus,
)

_DETERMINISTIC_CODES = {
    "AMBIGUOUS_DEPENDENCY_SOURCE",
    "CONFLICTING_PYTHON_METADATA",
    "DEPENDENCY_CONFLICT",
    "INCOMPATIBLE_PYTHON",
    "ENVIRONMENT_FINGERPRINT_MISMATCH",
    "INVALID_DEPENDENCY_METADATA",
    "INVALID_PYTHON_REQUIREMENT",
    "UNSUPPORTED_LOCK_FILE",
    "UNSUPPORTED_PROJECT_RUNNER",
}
_VERSION_CONFLICT = re.compile(r"require\s+([A-Za-z0-9_.-]+)==([^\s,]+)\s+and\s+\1==([^\s,]+)", re.IGNORECASE)
_AUDIT_LOGGER = logging.getLogger("promptopt.runtime.audit")


def _audit_runtime(action: str, project: ProjectRecord, *, error_code: str | None = None) -> None:
    """Emit identifiers and state only; diagnostics and owner data are intentionally excluded."""

    payload = {
        "action": action,
        "project_id": project.id,
        "environment_id": project.runtime_environment_id,
        "runtime_status": project.runtime_status.value,
        "build_status": project.runtime_build_status.value,
        "execution_status": project.runtime_execution_status.value,
    }
    fingerprint = project.runtime_dependency_fingerprint
    if fingerprint:
        payload["environment_fingerprint"] = fingerprint
    if error_code:
        payload["error_code"] = error_code
    _AUDIT_LOGGER.info("runtime_audit %s", json.dumps(payload, sort_keys=True, separators=(",", ":")))


def _diagnose_failure(error: str, report: RuntimeReport | None = None) -> RuntimeReport:
    """Normalize legacy free-form worker failures into the phase-6 API contract."""
    if report is not None and report.failure_stage and report.error_code:
        report.retryable = report.retryable and report.error_code not in _DETERMINISTIC_CODES
        if report.error:
            report.error = bounded_redacted_text(report.error, 4000)
        return report
    lowered = error.lower()
    if "fingerprint" in lowered and "does not match" in lowered:
        stage, code, retryable = FailureStage.BUILD, "ENVIRONMENT_FINGERPRINT_MISMATCH", False
    elif "dependency" in lowered and ("conflict" in lowered or "no solution" in lowered or "unsatisfiable" in lowered):
        stage, code, retryable = FailureStage.RESOLVE, "DEPENDENCY_CONFLICT", False
    elif "python" in lowered and ("incompatible" in lowered or "version" in lowered):
        stage, code, retryable = FailureStage.METADATA, "INCOMPATIBLE_PYTHON", False
    elif "timed out" in lowered or "timeout" in lowered:
        stage, code, retryable = FailureStage.BUILD, "RUNTIME_TIMEOUT", True
    elif "coverage" in lowered:
        stage, code, retryable = FailureStage.COVERAGE, "COVERAGE_FAILED", True
    elif "test" in lowered or "pytest" in lowered:
        stage, code, retryable = FailureStage.TEST, "TESTS_FAILED", True
    else:
        stage, code, retryable = FailureStage.BUILD, "RUNTIME_BUILD_FAILED", True
    conflicts = []
    if match := _VERSION_CONFLICT.search(error):
        conflicts.append(
            DependencyConflict(
                package=match.group(1),
                requested_versions=[match.group(2), match.group(3)],
            )
        )
    return RuntimeReport(
        status=RuntimeStatus.FAILED,
        error=bounded_redacted_text(error, 4000),
        failure_stage=stage,
        error_code=code,
        retryable=retryable,
        conflicts=conflicts,
    )


class CloudRunRuntimePreparer:
    """Build a candidate shared environment without mutating the active bundle."""

    def __init__(self, *, client, storage: ObjectStorage, bucket: str, job_name: str, timeout_seconds: int):
        self.client = client
        self.storage = storage
        self.bucket = bucket
        self.job_name = job_name
        self.timeout_seconds = timeout_seconds

    async def start(
        self,
        projects: list[ProjectRecord],
        *,
        reuse_bundle_object: str | None = None,
        expected_dependency_fingerprint: str | None = None,
    ) -> str:
        if not projects:
            raise ValueError("A runtime environment requires at least one project")
        execution_id = uuid4().hex
        prefix = f"runner-jobs/runtime/{execution_id}"
        manifest_object = f"{prefix}/inputs/environment.json"
        result_object = f"{prefix}/runtime_result.json"
        bundle_object = f"{prefix}/runtime.tar.gz"
        manifest_projects = []
        for project in projects:
            archive_object = f"{prefix}/inputs/projects/{project.id}.zip"
            archive = await self.storage.read(project.object_name)
            await self.storage.write(archive_object, archive, "application/zip")
            manifest_projects.append(
                {
                    "project_id": project.id,
                    "archive_object": archive_object,
                    "source_directory": project.settings.runtime.source_directory,
                    "test_directory": project.settings.tests.test_directory,
                }
            )
        await self.storage.write(
            manifest_object,
            json.dumps({"projects": manifest_projects}, separators=(",", ":")).encode(),
            "application/json",
        )
        timeout = min(max(project.settings.runtime.run_timeout_seconds for project in projects), self.timeout_seconds)
        output_limit = min(project.settings.security.maximum_output_bytes for project in projects)
        python_versions = {project.settings.runtime.python_version for project in projects}
        if len(python_versions) != 1:
            raise AppError(
                409,
                "PYTHON_VERSION_CONFLICT",
                "Projects in one runtime environment must use the same Python version",
            )
        args = [
            "-m",
            "cloud.prepare_runtime",
            "--bucket",
            self.bucket,
            "--manifest-object",
            manifest_object,
            "--result-object",
            result_object,
            "--bundle-object",
            bundle_object,
            "--python-version",
            python_versions.pop(),
            "--timeout-seconds",
            str(timeout),
            "--maximum-output-bytes",
            str(output_limit),
        ]
        if reuse_bundle_object:
            args.extend(["--reuse-bundle-object", reuse_bundle_object])
        if expected_dependency_fingerprint:
            args.extend(["--expected-dependency-fingerprint", expected_dependency_fingerprint])
        request = {
            "name": self.job_name,
            "overrides": {
                "container_overrides": [{"args": args, "env": []}],
                "task_count": 1,
                "timeout": f"{timeout}s",
            },
        }
        await asyncio.to_thread(self.client.run_job, request=request)
        return prefix

    async def collect(self, prefix: str) -> RuntimeReport | None:
        try:
            payload = json.loads((await self.storage.read(f"{prefix}/runtime_result.json")).decode())
        except Exception:
            return None
        payload.pop("project_root", None)
        for project in payload.get("projects", {}).values():
            if isinstance(project, dict):
                project.pop("project_root", None)
        return parse_runtime_report(payload)


class RuntimePreparer(Protocol):
    async def start(
        self,
        projects: list[ProjectRecord],
        *,
        reuse_bundle_object: str | None = None,
        expected_dependency_fingerprint: str | None = None,
    ) -> str: ...

    async def collect(self, prefix: str) -> RuntimeReport | None: ...


class RuntimePreparationService:
    def __init__(self, repository: ProjectRepository, runner: RuntimePreparer | None):
        self.repository = repository
        self.runner = runner

    async def request(self, project: ProjectRecord) -> ProjectResponse:
        if self.runner is None:
            raise AppError(503, "RUNTIME_PREPARER_UNAVAILABLE", "Runtime preparation is not configured")
        if project.runtime_status == RuntimeStatus.PREPARING:
            raise AppError(409, "RUNTIME_ALREADY_PREPARING", "Runtime preparation is already running")
        if not project.runtime_environment_id:
            raise AppError(409, "RUNTIME_ENVIRONMENT_REQUIRED", "Choose a runtime environment first")
        project.runtime_status = RuntimeStatus.QUEUED
        project.runtime_build_status = BuildStatus.QUEUED
        project.runtime_execution_status = ExecutionStatus.NOT_STARTED
        project.requested_python_version = project.settings.runtime.python_version
        project.runtime_report = None
        # Every retry gets a fresh deadline. Reusing the previous attempt's
        # timestamp makes a successful retry appear timed out immediately.
        project.runtime_started_at = datetime.now(UTC)
        project.runtime_finished_at = None
        project.updated_at = datetime.now(UTC)
        await self.repository.save(project)
        _audit_runtime("runtime_requested", project)
        await self._try_start(project)
        refreshed = await self.repository.get(project.id)
        return ProjectResponse.model_validate((refreshed or project).model_dump(exclude={"owner_id"}))

    async def retry_execution(self, project: ProjectRecord) -> ProjectResponse:
        if self.runner is None:
            raise AppError(503, "RUNTIME_PREPARER_UNAVAILABLE", "Runtime preparation is not configured")
        report = project.runtime_report
        bundle_object = (report.bundle_object if report else None) or project.runtime_bundle_object
        fingerprint = (
            report.environment_fingerprint or report.dependency_fingerprint if report else None
        ) or project.runtime_dependency_fingerprint
        if not bundle_object or not fingerprint:
            raise AppError(
                409,
                "RUNTIME_ARTIFACT_NOT_REUSABLE",
                "No immutable runtime artifact is available for execution retry",
            )
        owner_projects = await self.repository.list_for_owner(project.owner_id)
        environment_projects = [
            item
            for item in owner_projects
            if item.runtime_environment_id == project.runtime_environment_id
            and (item.id == project.id or item.runtime_status == RuntimeStatus.READY)
        ]
        now = datetime.now(UTC)
        project.runtime_status = RuntimeStatus.QUEUED
        project.runtime_build_status = BuildStatus.READY
        project.runtime_execution_status = ExecutionStatus.QUEUED
        project.runtime_started_at = now
        project.runtime_finished_at = None
        project.runtime_report = None
        project.updated_at = now
        await self.repository.save(project)
        _audit_runtime("execution_retry_requested", project)
        try:
            project.runtime_artifact_prefix = await self.runner.start(
                environment_projects,
                reuse_bundle_object=bundle_object,
                expected_dependency_fingerprint=fingerprint,
            )
            project.runtime_status = RuntimeStatus.PREPARING
            project.runtime_build_status = BuildStatus.READY
            project.runtime_execution_status = ExecutionStatus.RUNNING
            _audit_runtime("execution_retry_started", project)
        except Exception as exc:
            project.runtime_status = RuntimeStatus.FAILED
            project.runtime_build_status = BuildStatus.READY
            project.runtime_execution_status = ExecutionStatus.FAILED
            project.runtime_report = _diagnose_failure(str(exc))
            project.runtime_finished_at = datetime.now(UTC)
            _audit_runtime("execution_retry_failed", project, error_code=project.runtime_report.error_code)
        project.updated_at = datetime.now(UTC)
        await self.repository.save(project)
        return ProjectResponse.model_validate(project.model_dump(exclude={"owner_id"}))

    async def _try_start(self, project: ProjectRecord) -> None:
        owner_projects = await self.repository.list_for_owner(project.owner_id)
        environment = [item for item in owner_projects if item.runtime_environment_id == project.runtime_environment_id]
        if any(item.id != project.id and item.runtime_status == RuntimeStatus.PREPARING for item in environment):
            return
        queued = sorted(
            (item for item in environment if item.runtime_status == RuntimeStatus.QUEUED),
            key=lambda item: (item.runtime_started_at or item.created_at, item.id),
        )
        if not queued or queued[0].id != project.id:
            return
        environment_projects = [
            item for item in environment if item.id != project.id and item.runtime_status == RuntimeStatus.READY
        ]
        try:
            project.runtime_artifact_prefix = await self.runner.start([*environment_projects, project])
            project.runtime_status = RuntimeStatus.PREPARING
            project.runtime_build_status = BuildStatus.BUILDING
            project.runtime_execution_status = ExecutionStatus.QUEUED
            _audit_runtime("runtime_build_started", project)
        except Exception as exc:
            project.runtime_status = RuntimeStatus.FAILED
            project.runtime_build_status = BuildStatus.FAILED
            project.runtime_execution_status = ExecutionStatus.NOT_STARTED
            project.runtime_report = _diagnose_failure(str(exc))
            project.runtime_finished_at = datetime.now(UTC)
            _audit_runtime("runtime_start_failed", project, error_code=project.runtime_report.error_code)
        project.updated_at = datetime.now(UTC)
        await self.repository.save(project)

    async def refresh(self, project: ProjectRecord) -> ProjectRecord:
        if self.runner is not None and project.runtime_status == RuntimeStatus.QUEUED:
            await self._try_start(project)
            return await self.repository.get(project.id) or project
        if (
            self.runner is None
            or project.runtime_status != RuntimeStatus.PREPARING
            or not project.runtime_artifact_prefix
        ):
            return project
        report = await self.runner.collect(project.runtime_artifact_prefix)
        if report is None:
            deadline = (project.runtime_started_at or datetime.now(UTC)) + timedelta(
                seconds=project.settings.runtime.run_timeout_seconds + 120
            )
            if datetime.now(UTC) >= deadline:
                await self._reject(project, "Runtime environment build timed out before publishing its result")
            return project
        if report.status != RuntimeStatus.READY or not report.bundle_object:
            await self._reject(project, report.error or "Runtime environment build failed", report)
            return project

        now = datetime.now(UTC)
        owner_projects = await self.repository.list_for_owner(project.owner_id)
        environment = [item for item in owner_projects if item.runtime_environment_id == project.runtime_environment_id]
        expected_members = {
            item.id for item in environment if item.id == project.id or item.runtime_status == RuntimeStatus.READY
        }
        if expected_members != set(report.projects):
            await self._reject(
                project,
                "Runtime result is stale because the environment membership changed while it was building",
            )
            return project
        members = {item.id: item for item in environment if item.id in report.projects}
        if set(members) != set(report.projects):
            await self._reject(project, "Runtime result does not match the environment membership snapshot")
            return project
        for project_id, member_report in report.projects.items():
            member = members[project_id]
            member.runtime_status = RuntimeStatus.READY
            member.runtime_build_status = BuildStatus.READY
            member.runtime_execution_status = ExecutionStatus.SUCCEEDED
            member.runtime_bundle_object = report.bundle_object
            member.runtime_dependency_fingerprint = report.dependency_fingerprint
            member.requested_python_version = report.requested_python_version or member.settings.runtime.python_version
            member.detected_python_version = report.detected_python_version or member.detected_python_version
            member.resolved_python_version = report.resolved_python_version or member.settings.runtime.python_version
            member.runtime_artifact_prefix = project.runtime_artifact_prefix
            member.runtime_report = self._member_report(report, member_report)
            member.runtime_finished_at = now
            member.updated_at = now
            member.settings.runtime.source_directory = member_report.source_directory
            member.settings.tests.test_directory = member_report.test_directory
            await self.repository.save(member)
            _audit_runtime("runtime_activated", member)
        return members[project.id]

    async def _reject(self, project: ProjectRecord, error: str, report: RuntimeReport | None = None) -> None:
        project.runtime_status = RuntimeStatus.FAILED
        project.runtime_report = _diagnose_failure(error, report)
        project.detected_python_version = (
            project.runtime_report.detected_python_version or project.detected_python_version
        )
        project.resolved_python_version = (
            project.runtime_report.resolved_python_version or project.resolved_python_version
        )
        if project.runtime_report.failure_stage in {
            FailureStage.COLLECT,
            FailureStage.TEST,
            FailureStage.COVERAGE,
        }:
            project.runtime_build_status = BuildStatus.READY
            project.runtime_execution_status = ExecutionStatus.FAILED
        else:
            project.runtime_build_status = BuildStatus.FAILED
            project.runtime_execution_status = ExecutionStatus.NOT_STARTED
        project.runtime_finished_at = datetime.now(UTC)
        project.updated_at = project.runtime_finished_at
        await self.repository.save(project)
        _audit_runtime("runtime_rejected", project, error_code=project.runtime_report.error_code)

    @staticmethod
    def _member_report(report: RuntimeReport, member: RuntimeProjectReport) -> RuntimeReport:
        return RuntimeReport(
            status=RuntimeStatus.READY,
            source_directory=member.source_directory,
            test_directory=member.test_directory,
            dependency_files=member.dependency_files,
            install_strategy=report.install_strategy,
            collected_tests=member.collected_tests,
            statement_coverage=member.statement_coverage,
            branch_coverage=member.branch_coverage,
            projects=report.projects,
            dependency_fingerprint=report.dependency_fingerprint,
            environment_fingerprint=report.environment_fingerprint or report.dependency_fingerprint,
            requested_python_version=report.requested_python_version,
            detected_python_version=report.detected_python_version,
            resolved_python_version=report.resolved_python_version,
            runner_profile=report.runner_profile,
            pytest_version=report.pytest_version,
            coverage_version=report.coverage_version,
            bundle_object=report.bundle_object,
            protocol_version=report.protocol_version,
        )
