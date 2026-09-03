from datetime import UTC, datetime, timedelta
from zipfile import ZipFile

import pytest
from cloud.runtime_workspace import RuntimeProjectSpec, prepare_environment

from backend.core.errors import AppError
from backend.modules.projects.repository import InMemoryProjectRepository
from backend.modules.projects.runtime import (
    CloudRunRuntimePreparer,
    RuntimePreparationService,
    _audit_runtime,
    _diagnose_failure,
)
from backend.modules.projects.schemas import (
    ProjectRecord,
    ProjectSettings,
    ProjectStatus,
    RuntimeProjectReport,
    RuntimeReport,
    RuntimeStatus,
)
from backend.modules.projects.service import ProjectService


def project(project_id: str, *, status: RuntimeStatus, bundle: str | None = None) -> ProjectRecord:
    now = datetime.now(UTC)
    return ProjectRecord(
        id=project_id,
        owner_id="owner",
        name=project_id,
        description="",
        upload_id=f"upload-{project_id}",
        object_name=f"uploads/{project_id}.zip",
        branch="main",
        commit=None,
        status=ProjectStatus.READY,
        settings=ProjectSettings(),
        runtime_environment_id="shared-environment",
        runtime_environment_name="Shared Python 3.12",
        runtime_status=status,
        runtime_bundle_object=bundle,
        created_at=now,
        updated_at=now,
    )


class FakeRunner:
    def __init__(self, report: RuntimeReport):
        self.report = report
        self.started_with: list[str] = []
        self.start_calls: list[list[str]] = []
        self.start_options: list[dict] = []

    async def start(self, projects, **options):
        self.started_with = [item.id for item in projects]
        self.start_calls.append(self.started_with)
        self.start_options.append(options)
        return "runner-jobs/runtime/candidate"

    async def collect(self, prefix):
        assert prefix == "runner-jobs/runtime/candidate"
        return self.report


def test_runtime_diagnostics_and_audit_logs_do_not_leak_secrets(caplog):
    caplog.set_level("INFO", logger="promptopt.runtime.audit")
    candidate = project("candidate", status=RuntimeStatus.FAILED)
    candidate.owner_id = "private-owner"

    report = _diagnose_failure("API_TOKEN=do-not-log dependency conflict")
    _audit_runtime("runtime_rejected", candidate, error_code=report.error_code)

    assert "do-not-log" not in (report.error or "")
    assert "private-owner" not in caplog.text
    assert "candidate" in caplog.text
    assert "runtime_rejected" in caplog.text


@pytest.mark.asyncio
async def test_conflicting_candidate_is_rejected_without_replacing_active_bundle():
    repository = InMemoryProjectRepository()
    existing = project("existing", status=RuntimeStatus.READY, bundle="runtime/active.tar.gz")
    candidate = project("candidate", status=RuntimeStatus.NOT_REQUESTED)
    await repository.create(existing)
    await repository.create(candidate)
    runner = FakeRunner(
        RuntimeReport(
            status=RuntimeStatus.FAILED,
            error=(
                "Dependency conflict: Because you require coverage==7.15.2 and "
                "coverage==7.10.7, your requirements are unsatisfiable"
            ),
        )
    )
    service = RuntimePreparationService(repository, runner)

    queued = await service.request(candidate)
    assert queued.runtime_status == RuntimeStatus.PREPARING
    assert runner.started_with == ["existing", "candidate"]
    rejected = await service.refresh(candidate)

    assert rejected.runtime_status == RuntimeStatus.FAILED
    assert "Dependency conflict" in (rejected.runtime_report.error or "")
    assert rejected.runtime_report.failure_stage == "resolve"
    assert rejected.runtime_report.error_code == "DEPENDENCY_CONFLICT"
    assert rejected.runtime_report.retryable is False
    assert rejected.runtime_report.conflicts[0].package == "coverage"
    assert rejected.runtime_report.conflicts[0].requested_versions == ["7.15.2", "7.10.7"]
    assert rejected.runtime_build_status == "failed"
    assert rejected.runtime_execution_status == "not_started"
    unchanged = await repository.get("existing")
    assert unchanged.runtime_status == RuntimeStatus.READY
    assert unchanged.runtime_bundle_object == "runtime/active.tar.gz"


@pytest.mark.asyncio
async def test_compatible_candidate_atomically_replaces_bundle_for_all_members():
    repository = InMemoryProjectRepository()
    existing = project("existing", status=RuntimeStatus.READY, bundle="runtime/active.tar.gz")
    candidate = project("candidate", status=RuntimeStatus.NOT_REQUESTED)
    await repository.create(existing)
    await repository.create(candidate)
    members = {
        project_id: RuntimeProjectReport(
            source_directory="pkg",
            test_directory="tests",
            collected_tests=1,
            statement_coverage=1.0,
            branch_coverage=1.0,
        )
        for project_id in ("existing", "candidate")
    }
    runner = FakeRunner(
        RuntimeReport(
            status=RuntimeStatus.READY,
            projects=members,
            install_strategy="uv shared resolution",
            dependency_fingerprint="digest-2",
            bundle_object="runtime/candidate.tar.gz",
            protocol_version=2,
        )
    )
    service = RuntimePreparationService(repository, runner)

    await service.request(candidate)
    accepted = await service.refresh(candidate)

    assert accepted.runtime_status == RuntimeStatus.READY
    for project_id in ("existing", "candidate"):
        member = await repository.get(project_id)
        assert member.runtime_bundle_object == "runtime/candidate.tar.gz"
        assert member.runtime_dependency_fingerprint == "digest-2"
        assert member.runtime_status == RuntimeStatus.READY
        assert member.runtime_build_status == "ready"
        assert member.runtime_execution_status == "succeeded"
        assert member.resolved_python_version == "3.12"


@pytest.mark.asyncio
async def test_stale_runtime_result_cannot_overwrite_new_environment_membership():
    repository = InMemoryProjectRepository()
    existing = project("existing", status=RuntimeStatus.READY, bundle="runtime/active.tar.gz")
    candidate = project("candidate", status=RuntimeStatus.NOT_REQUESTED)
    await repository.create(existing)
    await repository.create(candidate)
    members = {
        project_id: RuntimeProjectReport(source_directory="pkg", test_directory="tests")
        for project_id in ("existing", "candidate")
    }
    runner = FakeRunner(
        RuntimeReport(
            status=RuntimeStatus.READY,
            projects=members,
            dependency_fingerprint="stale-digest",
            bundle_object="runtime/stale.tar.gz",
        )
    )
    service = RuntimePreparationService(repository, runner)

    await service.request(candidate)
    concurrent_member = project("concurrent-member", status=RuntimeStatus.READY, bundle="runtime/new-active.tar.gz")
    await repository.create(concurrent_member)
    rejected = await service.refresh(candidate)

    assert rejected.runtime_status == RuntimeStatus.FAILED
    assert "membership changed" in (rejected.runtime_report.error or "")
    assert (await repository.get("existing")).runtime_bundle_object == "runtime/active.tar.gz"
    assert (await repository.get("concurrent-member")).runtime_bundle_object == "runtime/new-active.tar.gz"


@pytest.mark.asyncio
async def test_environment_rebuilds_are_queued_instead_of_rejected_as_busy():
    repository = InMemoryProjectRepository()
    first = project("first", status=RuntimeStatus.NOT_REQUESTED)
    second = project("second", status=RuntimeStatus.NOT_REQUESTED)
    first.created_at = first.created_at.replace(microsecond=1)
    second.created_at = second.created_at.replace(microsecond=2)
    await repository.create(first)
    await repository.create(second)
    runner = FakeRunner(RuntimeReport(status=RuntimeStatus.FAILED, error="pending"))
    service = RuntimePreparationService(repository, runner)

    first_response = await service.request(first)
    second_response = await service.request(second)

    assert first_response.runtime_status == RuntimeStatus.PREPARING
    assert second_response.runtime_status == RuntimeStatus.QUEUED
    assert runner.start_calls == [["first"]]


@pytest.mark.asyncio
async def test_runtime_retry_resets_the_attempt_deadline():
    repository = InMemoryProjectRepository()
    candidate = project("candidate", status=RuntimeStatus.FAILED)
    previous_started_at = datetime.now(UTC) - timedelta(hours=2)
    candidate.runtime_started_at = previous_started_at
    await repository.create(candidate)
    runner = FakeRunner(RuntimeReport(status=RuntimeStatus.FAILED, error="pending"))
    service = RuntimePreparationService(repository, runner)

    retried = await service.request(candidate)

    assert retried.runtime_started_at is not None
    assert retried.runtime_started_at > previous_started_at + timedelta(hours=1)
    assert retried.runtime_status == RuntimeStatus.PREPARING


@pytest.mark.asyncio
async def test_deterministic_dependency_conflict_cannot_use_retry_endpoint():
    repository = InMemoryProjectRepository()
    candidate = project("candidate", status=RuntimeStatus.FAILED)
    candidate.runtime_report = RuntimeReport(
        status=RuntimeStatus.FAILED,
        failure_stage="resolve",
        error_code="DEPENDENCY_CONFLICT",
        retryable=False,
        error="requirements are unsatisfiable",
    )
    await repository.create(candidate)
    projects = ProjectService(repository, uploads=None)  # type: ignore[arg-type]
    projects.set_runtime_service(RuntimePreparationService(repository, FakeRunner(candidate.runtime_report)))

    with pytest.raises(AppError) as caught:
        await projects.retry_runtime_build(candidate.id, candidate.owner_id)

    assert caught.value.code == "RUNTIME_BUILD_NOT_RETRYABLE"


@pytest.mark.asyncio
async def test_transient_execution_retry_keeps_active_artifact_until_admission():
    repository = InMemoryProjectRepository()
    candidate = project("candidate", status=RuntimeStatus.FAILED, bundle="runtime/active.tar.gz")
    candidate.runtime_dependency_fingerprint = "active-fingerprint"
    candidate.resolved_python_version = "3.12"
    candidate.runtime_report = RuntimeReport(
        status=RuntimeStatus.FAILED,
        failure_stage="coverage",
        error_code="COVERAGE_TIMEOUT",
        retryable=True,
        error="coverage timed out",
    )
    await repository.create(candidate)
    runner = FakeRunner(candidate.runtime_report)
    projects = ProjectService(repository, uploads=None)  # type: ignore[arg-type]
    projects.set_runtime_service(RuntimePreparationService(repository, runner))

    retried = await projects.retry_runtime_execution(candidate.id, candidate.owner_id)

    assert retried.runtime_status == RuntimeStatus.PREPARING
    assert retried.runtime_build_status == "ready"
    assert retried.runtime_execution_status == "running"
    assert retried.runtime_bundle_object == "runtime/active.tar.gz"
    assert retried.runtime_dependency_fingerprint == "active-fingerprint"
    assert retried.resolved_python_version == "3.12"
    assert runner.start_options == [
        {
            "reuse_bundle_object": "runtime/active.tar.gz",
            "expected_dependency_fingerprint": "active-fingerprint",
        }
    ]


@pytest.mark.asyncio
async def test_cloud_runtime_result_hides_worker_paths_before_validation():
    class Storage:
        async def read(self, object_name):
            assert object_name == "prefix/runtime_result.json"
            return (
                b'{"status":"runtime_ready","project_root":"/tmp/root",'
                b'"bundle_object":"prefix/runtime.tar.gz","projects":{'
                b'"project-1":{"project_root":"/tmp/root/project",'
                b'"source_directory":"pkg","test_directory":"tests"}}}'
            )

    preparer = CloudRunRuntimePreparer(
        client=None,
        storage=Storage(),
        bucket="bucket",
        job_name="job",
        timeout_seconds=900,
    )

    report = await preparer.collect("prefix")

    assert report is not None
    assert report.projects["project-1"].source_directory == "pkg"


def test_execution_retry_rejects_artifact_when_fingerprint_changed(tmp_path):
    archive = tmp_path / "project.zip"
    with ZipFile(archive, "w") as bundle:
        bundle.writestr("src/demo.py", "VALUE = 1\n")

    result, python = prepare_environment(
        [RuntimeProjectSpec("project", archive, "src", "tests")],
        tmp_path / "workspace",
        reuse_bundle=tmp_path / "runtime.tar.gz",
        expected_dependency_fingerprint="stale-fingerprint",
    )

    assert python is None
    assert result.status == "runtime_failed"
    assert "fingerprint does not match" in (result.error or "")
