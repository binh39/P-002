import asyncio
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from backend.core.errors import AppError
from backend.infrastructure.storage import ObjectStorage

from .repository import ProjectRepository
from .schemas import ProjectRecord, ProjectResponse, RuntimeProjectReport, RuntimeReport, RuntimeStatus


class CloudRunRuntimePreparer:
    """Build a candidate shared environment without mutating the active bundle."""

    def __init__(self, *, client, storage: ObjectStorage, bucket: str, job_name: str, timeout_seconds: int):
        self.client = client
        self.storage = storage
        self.bucket = bucket
        self.job_name = job_name
        self.timeout_seconds = timeout_seconds

    async def start(self, projects: list[ProjectRecord]) -> str:
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
        return RuntimeReport.model_validate(payload)


class RuntimePreparationService:
    def __init__(self, repository: ProjectRepository, runner: CloudRunRuntimePreparer | None):
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
        project.runtime_report = None
        # Every retry gets a fresh deadline. Reusing the previous attempt's
        # timestamp makes a successful retry appear timed out immediately.
        project.runtime_started_at = datetime.now(UTC)
        project.runtime_finished_at = None
        project.updated_at = datetime.now(UTC)
        await self.repository.save(project)
        await self._try_start(project)
        refreshed = await self.repository.get(project.id)
        return ProjectResponse.model_validate((refreshed or project).model_dump(exclude={"owner_id"}))

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
        except Exception as exc:
            project.runtime_status = RuntimeStatus.FAILED
            project.runtime_report = RuntimeReport(status=RuntimeStatus.FAILED, error=str(exc)[-4000:])
            project.runtime_finished_at = datetime.now(UTC)
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
            await self._reject(project, report.error or "Runtime environment build failed")
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
            member.runtime_bundle_object = report.bundle_object
            member.runtime_dependency_fingerprint = report.dependency_fingerprint
            member.runtime_artifact_prefix = project.runtime_artifact_prefix
            member.runtime_report = self._member_report(report, member_report)
            member.runtime_finished_at = now
            member.updated_at = now
            member.settings.runtime.source_directory = member_report.source_directory
            member.settings.tests.test_directory = member_report.test_directory
            await self.repository.save(member)
        return members[project.id]

    async def _reject(self, project: ProjectRecord, error: str) -> None:
        project.runtime_status = RuntimeStatus.FAILED
        project.runtime_report = RuntimeReport(status=RuntimeStatus.FAILED, error=error[-4000:])
        project.runtime_finished_at = datetime.now(UTC)
        project.updated_at = project.runtime_finished_at
        await self.repository.save(project)

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
            bundle_object=report.bundle_object,
            protocol_version=report.protocol_version,
        )
