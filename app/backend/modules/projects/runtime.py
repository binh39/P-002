import asyncio
import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from backend.core.errors import AppError
from backend.infrastructure.storage import ObjectStorage

from .repository import ProjectRepository
from .schemas import (
    MINIMUM_RUNTIME_PROTOCOL_VERSION,
    PREPARED_RUNTIME_PROTOCOL_VERSION,
    RUNTIME_EXECUTION_MODE_GENERIC,
    RUNTIME_EXECUTION_MODE_PROJECT_IMAGE,
    ProjectRecord,
    ProjectResponse,
    RuntimeProjectReport,
    RuntimeReport,
    RuntimeStatus,
)


def _bind_runtime_identity(report: RuntimeReport) -> str:
    """Bind the admitted protocol/mode to the prepared runtime digest.

    The preparer first computes a capsule digest before the API knows whether
    the project will use the generic bundle or legacy project-image path.  The
    admission digest must nevertheless distinguish those execution contracts,
    otherwise a resume/cache lookup could reuse an artifact under a different
    worker protocol.
    """
    payload = {
        "prepared_runtime": report.runtime_digest,
        "source_archive_sha256": report.source_archive_sha256,
        "runtime_bundle_sha256": report.runtime_bundle_sha256,
        "runtime_image": report.runtime_image,
        "runtime_worker_job": report.runtime_worker_job,
        "runtime_protocol_version": report.protocol_version,
        "execution_mode": report.execution_mode,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _is_sha256(value: str | None) -> bool:
    return bool(value and re.fullmatch(r"[0-9a-f]{64}", value))


class CloudRunRuntimePreparer:
    """Build one immutable runtime artifact for one uploaded project.

    A project archive is never resolved together with another project's
    dependencies.  ``runtime_environment_id`` remains grouping metadata for
    the UI, not a shared virtual environment.
    """

    def __init__(
        self,
        *,
        client,
        storage: ObjectStorage,
        bucket: str,
        job_name: str,
        timeout_seconds: int,
        job_names: dict[str, str] | None = None,
    ):
        self.client = client
        self.storage = storage
        self.bucket = bucket
        self.job_name = job_name
        self.job_names = dict(job_names or {"3.12": job_name})
        self.timeout_seconds = timeout_seconds

    async def start(self, projects: list[ProjectRecord]) -> str:
        if len(projects) != 1:
            raise ValueError("Runtime preparation requires exactly one project")
        project = projects[0]
        python_version = project.settings.runtime.python_version
        selected_job = self.job_names.get(python_version)
        if not selected_job:
            raise AppError(
                422,
                "PYTHON_RUNTIME_UNAVAILABLE",
                f"No isolated runtime worker is deployed for Python {python_version}",
            )
        execution_id = uuid4().hex
        prefix = f"runner-jobs/runtime/{execution_id}"
        manifest_object = f"{prefix}/inputs/environment.json"
        result_object = f"{prefix}/runtime_result.json"
        bundle_object = f"{prefix}/runtime.tar.gz"
        archive_object = f"{prefix}/inputs/projects/{project.id}.zip"
        archive = await self.storage.read(project.object_name)
        await self.storage.write(archive_object, archive, "application/zip")
        manifest_projects = [
            {
                "project_id": project.id,
                "archive_object": archive_object,
                "source_directory": project.settings.runtime.source_directory,
                "test_directory": project.settings.tests.test_directory,
                "requirements_file": project.settings.dependencies.requirements_file,
                "lock_file": project.settings.dependencies.lock_file,
                "extra_package_index": project.settings.dependencies.extra_package_index,
                "install_command": project.settings.dependencies.install_command,
                "network_access": project.settings.security.network_access,
            }
        ]
        await self.storage.write(
            manifest_object,
            json.dumps({"projects": manifest_projects}, separators=(",", ":")).encode(),
            "application/json",
        )
        timeout = min(project.settings.runtime.run_timeout_seconds, self.timeout_seconds)
        output_limit = project.settings.security.maximum_output_bytes
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
            project.settings.runtime.python_version,
            "--timeout-seconds",
            str(timeout),
            "--maximum-output-bytes",
            str(output_limit),
        ]
        request = {
            "name": selected_job,
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


class CloudRunRuntimeImageFactory:
    """Create the content-addressed OCI image and dedicated worker job.

    This trusted job never imports or executes uploaded source. It only packages
    the already prepared capsule and asks Cloud Build/Cloud Run to materialize
    the immutable project worker.
    """

    def __init__(
        self,
        *,
        client,
        storage: ObjectStorage,
        bucket: str,
        job_name: str,
        cloud_project_id: str,
        region: str,
        image_repository: str,
        runner_service_account: str,
        build_service_account: str,
        model_project_id: str,
        coverup_model: str,
        timeout_seconds: int,
    ):
        self.client = client
        self.storage = storage
        self.bucket = bucket
        self.job_name = job_name
        self.cloud_project_id = cloud_project_id
        self.region = region
        self.image_repository = image_repository.rstrip("/")
        self.runner_service_account = runner_service_account
        self.build_service_account = build_service_account
        self.model_project_id = model_project_id
        self.coverup_model = coverup_model
        self.timeout_seconds = timeout_seconds

    async def start(
        self,
        project: ProjectRecord,
        prepared: RuntimeReport,
        preparation_prefix: str,
    ) -> str:
        if not prepared.bundle_object or not prepared.runtime_digest or not prepared.runtime_image:
            raise ValueError("Prepared runtime is incomplete")
        execution_id = uuid4().hex
        prefix = f"runner-jobs/runtime-images/{execution_id}"
        request_object = f"{prefix}/request.json"
        result_object = f"{prefix}/result.json"
        context_object = f"{prefix}/context.tar.gz"
        source_object = f"{preparation_prefix}/inputs/projects/{project.id}.zip"
        request = {
            "schema_version": 1,
            "project_id": project.id,
            "bucket": self.bucket,
            "cloud_project_id": self.cloud_project_id,
            "region": self.region,
            "image_repository": self.image_repository,
            "runner_service_account": self.runner_service_account,
            "build_service_account": self.build_service_account,
            "model_project_id": self.model_project_id,
            "coverup_model": self.coverup_model,
            "source_object": source_object,
            "runtime_bundle_object": prepared.bundle_object,
            "context_object": context_object,
            "source_archive_sha256": prepared.source_archive_sha256,
            "runtime_bundle_sha256": prepared.runtime_bundle_sha256,
            "base_runtime_image": prepared.runtime_image,
            "runtime_digest": prepared.runtime_digest,
            "build_timeout_seconds": min(self.timeout_seconds, 1800),
            "prepared_report": prepared.model_dump(mode="json"),
        }
        await self.storage.write(
            request_object,
            json.dumps(request, separators=(",", ":")).encode(),
            "application/json",
        )
        args = [
            "-m",
            "cloud.runtime_image_factory",
            "--bucket",
            self.bucket,
            "--request-object",
            request_object,
            "--result-object",
            result_object,
        ]
        api_request = {
            "name": self.job_name,
            "overrides": {
                "container_overrides": [{"args": args, "env": []}],
                "task_count": 1,
                "timeout": f"{self.timeout_seconds}s",
            },
        }
        await asyncio.to_thread(self.client.run_job, request=api_request)
        return prefix

    async def collect(self, prefix: str) -> RuntimeReport | None:
        try:
            payload = json.loads((await self.storage.read(f"{prefix}/result.json")).decode())
        except Exception:
            return None
        return RuntimeReport.model_validate(payload)


class RuntimePreparationService:
    def __init__(
        self,
        repository: ProjectRepository,
        runner: CloudRunRuntimePreparer | None,
        image_factory: CloudRunRuntimeImageFactory | None = None,
        execution_mode: str | None = None,
    ):
        self.repository = repository
        self.runner = runner
        self.image_factory = image_factory
        # Passing a factory explicitly preserves the legacy project-image
        # contract for callers/tests; production config selects the mode
        # explicitly and defaults to the generic worker + bundle contract.
        self.execution_mode = execution_mode or (
            RUNTIME_EXECUTION_MODE_PROJECT_IMAGE if image_factory is not None else RUNTIME_EXECUTION_MODE_GENERIC
        )

    async def request(self, project: ProjectRecord) -> ProjectResponse:
        if self.runner is None:
            raise AppError(503, "RUNTIME_PREPARER_UNAVAILABLE", "Runtime preparation is not configured")
        if project.runtime_status == RuntimeStatus.PREPARING:
            raise AppError(409, "RUNTIME_ALREADY_PREPARING", "Runtime preparation is already running")
        if not project.runtime_environment_id:
            raise AppError(409, "RUNTIME_ENVIRONMENT_REQUIRED", "Choose a runtime environment first")
        project.runtime_status = RuntimeStatus.QUEUED
        project.runtime_report = None
        project.runtime_factory_prefix = None
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
        if project.runtime_status != RuntimeStatus.QUEUED:
            return
        try:
            project.runtime_artifact_prefix = await self.runner.start([project])
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
        if project.runtime_factory_prefix:
            if self.image_factory is None:
                await self._reject(project, "Runtime image factory is not configured")
                return project
            report = await self.image_factory.collect(project.runtime_factory_prefix)
            if report is None:
                await self._reject_if_timed_out(
                    project,
                    "Runtime image build timed out before publishing its result",
                    timeout_seconds=self.image_factory.timeout_seconds + 120,
                )
                return project
            if not self._complete_runtime_report(report):
                await self._reject(
                    project,
                    report.error or "Runtime image factory did not publish a complete immutable worker identity",
                )
                return project
            prepared = project.runtime_report
            if prepared is None or (
                report.runtime_image == prepared.runtime_image
                or report.runtime_worker_job == prepared.runtime_worker_job
            ):
                await self._reject(
                    project,
                    "Runtime image factory reused the generic preparation worker instead of creating a project-specific worker",
                )
                return project
            return await self._accept(project, report)
        report = await self.runner.collect(project.runtime_artifact_prefix)
        if report is None:
            await self._reject_if_timed_out(project, "Runtime preparation timed out before publishing its result")
            return project
        if report.status == RuntimeStatus.READY and set(report.projects) != {project.id}:
            await self._reject(project, "Runtime result does not match the immutable project snapshot")
            return project
        if report.status == RuntimeStatus.READY and report.protocol_version < PREPARED_RUNTIME_PROTOCOL_VERSION:
            await self._reject(
                project,
                "Runtime preparation protocol is outdated; rebuild the project runtime",
            )
            return project
        if (
            report.status != RuntimeStatus.READY
            or not report.bundle_object
            or not report.runtime_digest
            or not report.runtime_image
            or not report.source_archive_sha256
            or not report.runtime_bundle_sha256
        ):
            await self._reject(
                project,
                report.error or "Runtime preparation did not publish a complete immutable worker identity",
            )
            return project

        if self.execution_mode == RUNTIME_EXECUTION_MODE_PROJECT_IMAGE and self.image_factory is not None:
            try:
                project.runtime_factory_prefix = await self.image_factory.start(
                    project,
                    report,
                    project.runtime_artifact_prefix,
                )
            except Exception as exc:
                await self._reject(project, str(exc))
                return project
            project.runtime_report = report
            project.runtime_started_at = datetime.now(UTC)
            project.updated_at = project.runtime_started_at
            await self.repository.save(project)
            return project

        if not self._complete_prepared_report(report):
            await self._reject(project, "Runtime preparation did not publish a complete runtime bundle")
            return project
        report.protocol_version = MINIMUM_RUNTIME_PROTOCOL_VERSION
        report.execution_mode = RUNTIME_EXECUTION_MODE_GENERIC
        report.runtime_digest = _bind_runtime_identity(report)
        return await self._accept(project, report)

    @staticmethod
    def _complete_prepared_report(report: RuntimeReport) -> bool:
        immutable_image = bool(
            report.runtime_image and re.fullmatch(r"[A-Za-z0-9._:/-]+@sha256:[0-9a-f]{64}", report.runtime_image)
        )
        return bool(
            report.status == RuntimeStatus.READY
            and report.protocol_version >= PREPARED_RUNTIME_PROTOCOL_VERSION
            and report.bundle_object
            and _is_sha256(report.runtime_digest)
            and immutable_image
            and report.runtime_worker_job
            and _is_sha256(report.source_archive_sha256)
            and report.source_archive_object
            and _is_sha256(report.runtime_bundle_sha256)
        )

    @staticmethod
    def _complete_runtime_report(report: RuntimeReport) -> bool:
        return bool(
            RuntimePreparationService._complete_prepared_report(report)
            and report.protocol_version
            >= (
                12
                if report.execution_mode == RUNTIME_EXECUTION_MODE_PROJECT_IMAGE
                else MINIMUM_RUNTIME_PROTOCOL_VERSION
            )
            and report.execution_mode in {RUNTIME_EXECUTION_MODE_GENERIC, RUNTIME_EXECUTION_MODE_PROJECT_IMAGE}
        )

    async def _accept(self, project: ProjectRecord, report: RuntimeReport) -> ProjectRecord:
        member_report = report.projects[project.id]
        now = datetime.now(UTC)
        project.runtime_status = RuntimeStatus.READY
        project.runtime_bundle_object = report.bundle_object
        project.runtime_dependency_fingerprint = report.dependency_fingerprint
        project.runtime_digest = report.runtime_digest or report.dependency_fingerprint
        project.runtime_image = report.runtime_image or project.settings.runtime.runtime_image
        project.runtime_worker_job = report.runtime_worker_job
        project.runtime_execution_mode = report.execution_mode
        project.source_archive_sha256 = report.source_archive_sha256
        project.runtime_source_archive_object = report.source_archive_object
        project.runtime_source_archive_generation = report.source_archive_generation
        project.runtime_bundle_sha256 = report.runtime_bundle_sha256
        project.runtime_bundle_generation = report.runtime_bundle_generation
        project.runtime_report = self._member_report(report, member_report)
        project.runtime_finished_at = now
        project.updated_at = now
        project.settings.runtime.source_directory = member_report.source_directory
        project.settings.tests.test_directory = member_report.test_directory
        await self.repository.save(project)
        return project

    async def _reject_if_timed_out(
        self,
        project: ProjectRecord,
        message: str,
        *,
        timeout_seconds: int | None = None,
    ) -> None:
        deadline = (project.runtime_started_at or datetime.now(UTC)) + timedelta(
            seconds=timeout_seconds or project.settings.runtime.run_timeout_seconds + 120
        )
        if datetime.now(UTC) >= deadline:
            await self._reject(project, message)

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
            runtime_digest=report.runtime_digest,
            python_version=report.python_version,
            runtime_image=report.runtime_image,
            runtime_worker_job=report.runtime_worker_job,
            source_archive_sha256=report.source_archive_sha256,
            source_archive_object=report.source_archive_object,
            source_archive_generation=report.source_archive_generation,
            runtime_bundle_sha256=report.runtime_bundle_sha256,
            runtime_bundle_generation=report.runtime_bundle_generation,
            network_access=report.network_access,
            bundle_object=report.bundle_object,
            protocol_version=report.protocol_version,
            execution_mode=report.execution_mode,
        )
