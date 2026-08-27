from datetime import UTC, datetime, timedelta

import pytest

from backend.modules.projects.repository import InMemoryProjectRepository
from backend.modules.projects.runtime import CloudRunRuntimePreparer, RuntimePreparationService
from backend.modules.projects.schemas import (
    MINIMUM_RUNTIME_PROTOCOL_VERSION,
    PREPARED_RUNTIME_PROTOCOL_VERSION,
    ProjectRecord,
    ProjectSettings,
    ProjectStatus,
    RuntimeProjectReport,
    RuntimeReport,
    RuntimeStatus,
)


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

    async def start(self, projects):
        self.started_with = [item.id for item in projects]
        self.start_calls.append(self.started_with)
        return "runner-jobs/runtime/candidate"

    async def collect(self, prefix):
        assert prefix == "runner-jobs/runtime/candidate"
        return self.report


class FakeFactory:
    def __init__(self, report: RuntimeReport):
        self.report = report
        self.started: list[tuple[str, str]] = []

    async def start(self, project, prepared, preparation_prefix):
        assert prepared.protocol_version == PREPARED_RUNTIME_PROTOCOL_VERSION
        self.started.append((project.id, preparation_prefix))
        return f"runner-jobs/runtime-images/{project.id}"

    async def collect(self, prefix):
        assert prefix.startswith("runner-jobs/runtime-images/")
        return self.report


@pytest.mark.asyncio
async def test_conflicting_project_is_rejected_without_touching_another_project_runtime():
    repository = InMemoryProjectRepository()
    existing = project("existing", status=RuntimeStatus.READY, bundle="runtime/active.tar.gz")
    candidate = project("candidate", status=RuntimeStatus.NOT_REQUESTED)
    await repository.create(existing)
    await repository.create(candidate)
    runner = FakeRunner(
        RuntimeReport(
            status=RuntimeStatus.FAILED,
            error="Dependency conflict prevented this project from joining the environment",
        )
    )
    service = RuntimePreparationService(repository, runner)

    queued = await service.request(candidate)
    assert queued.runtime_status == RuntimeStatus.PREPARING
    assert runner.started_with == ["candidate"]
    rejected = await service.refresh(candidate)

    assert rejected.runtime_status == RuntimeStatus.FAILED
    assert "Dependency conflict" in (rejected.runtime_report.error or "")
    unchanged = await repository.get("existing")
    assert unchanged.runtime_status == RuntimeStatus.READY
    assert unchanged.runtime_bundle_object == "runtime/active.tar.gz"


@pytest.mark.asyncio
async def test_compatible_project_publishes_only_its_immutable_runtime():
    repository = InMemoryProjectRepository()
    existing = project("existing", status=RuntimeStatus.READY, bundle="runtime/active.tar.gz")
    candidate = project("candidate", status=RuntimeStatus.NOT_REQUESTED)
    await repository.create(existing)
    await repository.create(candidate)
    members = {
        "candidate": RuntimeProjectReport(
            source_directory="pkg",
            test_directory="tests",
            collected_tests=1,
            statement_coverage=1.0,
            branch_coverage=1.0,
        )
    }
    runner = FakeRunner(
        RuntimeReport(
            status=RuntimeStatus.READY,
            projects=members,
            install_strategy="uv isolated resolution",
            dependency_fingerprint="digest-2",
            runtime_digest="runtime-digest-2",
            python_version="3.12",
            runtime_image=f"promptopt-runtime-py312@sha256:{'a' * 64}",
            runtime_worker_job="projects/p/locations/r/jobs/eval-candidate",
            source_archive_sha256="a" * 64,
            runtime_bundle_sha256="b" * 64,
            bundle_object="runtime/candidate.tar.gz",
            protocol_version=MINIMUM_RUNTIME_PROTOCOL_VERSION,
        )
    )
    service = RuntimePreparationService(repository, runner)

    await service.request(candidate)
    accepted = await service.refresh(candidate)

    assert accepted.runtime_status == RuntimeStatus.READY
    member = await repository.get("candidate")
    assert member.runtime_bundle_object == "runtime/candidate.tar.gz"
    assert member.runtime_dependency_fingerprint == "digest-2"
    assert member.runtime_digest == "runtime-digest-2"
    assert member.runtime_worker_job == "projects/p/locations/r/jobs/eval-candidate"
    assert member.source_archive_sha256 == "a" * 64
    assert member.runtime_bundle_sha256 == "b" * 64
    assert member.runtime_status == RuntimeStatus.READY
    unchanged = await repository.get("existing")
    assert unchanged.runtime_bundle_object == "runtime/active.tar.gz"


@pytest.mark.asyncio
async def test_runtime_result_for_multiple_projects_is_rejected():
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
    assert "immutable project snapshot" in (rejected.runtime_report.error or "")
    assert (await repository.get("existing")).runtime_bundle_object == "runtime/active.tar.gz"
    assert (await repository.get("concurrent-member")).runtime_bundle_object == "runtime/new-active.tar.gz"


@pytest.mark.asyncio
async def test_ready_runtime_with_old_protocol_is_rejected_before_admission():
    repository = InMemoryProjectRepository()
    candidate = project("candidate", status=RuntimeStatus.NOT_REQUESTED)
    await repository.create(candidate)
    runner = FakeRunner(
        RuntimeReport(
            status=RuntimeStatus.READY,
            projects={
                "candidate": RuntimeProjectReport(
                    source_directory="pkg",
                    test_directory="tests",
                )
            },
            runtime_digest="runtime-digest",
            runtime_image="image@sha256:one",
            runtime_worker_job="projects/p/locations/r/jobs/worker",
            source_archive_sha256="a" * 64,
            runtime_bundle_sha256="b" * 64,
            bundle_object="runtime/candidate.tar.gz",
            protocol_version=PREPARED_RUNTIME_PROTOCOL_VERSION - 1,
        )
    )
    service = RuntimePreparationService(repository, runner)

    await service.request(candidate)
    rejected = await service.refresh(candidate)

    assert rejected.runtime_status == RuntimeStatus.FAILED
    assert "protocol is outdated" in (rejected.runtime_report.error or "")


@pytest.mark.asyncio
async def test_prepared_capsule_is_materialized_before_project_is_admitted():
    repository = InMemoryProjectRepository()
    candidate = project("candidate", status=RuntimeStatus.NOT_REQUESTED)
    await repository.create(candidate)
    member = RuntimeProjectReport(source_directory="pkg", test_directory="tests", collected_tests=3)
    prepared = RuntimeReport(
        status=RuntimeStatus.READY,
        projects={"candidate": member},
        dependency_fingerprint="dependency-digest",
        runtime_digest="prepared-digest",
        python_version="3.12",
        runtime_image=f"repo/runtime-base@sha256:{'a' * 64}",
        runtime_worker_job="projects/p/locations/r/jobs/generic-worker",
        source_archive_sha256="b" * 64,
        runtime_bundle_sha256="c" * 64,
        bundle_object="runner-jobs/runtime/candidate/runtime.tar.gz",
        protocol_version=PREPARED_RUNTIME_PROTOCOL_VERSION,
    )
    final = prepared.model_copy(
        update={
            "runtime_digest": "project-image-digest",
            "runtime_image": f"repo/project-candidate@sha256:{'d' * 64}",
            "runtime_worker_job": "projects/p/locations/r/jobs/eval-candidate-image",
            "protocol_version": MINIMUM_RUNTIME_PROTOCOL_VERSION,
        }
    )
    factory = FakeFactory(final)
    service = RuntimePreparationService(repository, FakeRunner(prepared), factory)

    await service.request(candidate)
    building = await service.refresh(candidate)
    assert building.runtime_status == RuntimeStatus.PREPARING
    assert building.runtime_factory_prefix == "runner-jobs/runtime-images/candidate"
    assert factory.started == [("candidate", "runner-jobs/runtime/candidate")]

    admitted = await service.refresh(building)
    assert admitted.runtime_status == RuntimeStatus.READY
    assert admitted.runtime_image == f"repo/project-candidate@sha256:{'d' * 64}"
    assert admitted.runtime_worker_job == "projects/p/locations/r/jobs/eval-candidate-image"
    assert admitted.runtime_report is not None
    assert admitted.runtime_report.protocol_version == MINIMUM_RUNTIME_PROTOCOL_VERSION


@pytest.mark.asyncio
async def test_factory_result_without_dedicated_worker_is_rejected():
    repository = InMemoryProjectRepository()
    candidate = project("candidate", status=RuntimeStatus.NOT_REQUESTED)
    await repository.create(candidate)
    member = RuntimeProjectReport(source_directory="pkg", test_directory="tests")
    prepared = RuntimeReport(
        status=RuntimeStatus.READY,
        projects={"candidate": member},
        runtime_digest="prepared-digest",
        runtime_image=f"repo/runtime-base@sha256:{'a' * 64}",
        runtime_worker_job="projects/p/locations/r/jobs/generic-worker",
        source_archive_sha256="b" * 64,
        runtime_bundle_sha256="c" * 64,
        bundle_object="runner-jobs/runtime/candidate/runtime.tar.gz",
        protocol_version=PREPARED_RUNTIME_PROTOCOL_VERSION,
    )
    incomplete = prepared.model_copy(
        update={"protocol_version": MINIMUM_RUNTIME_PROTOCOL_VERSION, "runtime_worker_job": None}
    )
    service = RuntimePreparationService(repository, FakeRunner(prepared), FakeFactory(incomplete))

    await service.request(candidate)
    building = await service.refresh(candidate)
    rejected = await service.refresh(building)

    assert rejected.runtime_status == RuntimeStatus.FAILED
    assert "complete immutable worker identity" in (rejected.runtime_report.error or "")


@pytest.mark.asyncio
async def test_project_runtime_builds_can_start_independently():
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
    assert second_response.runtime_status == RuntimeStatus.PREPARING
    assert runner.start_calls == [["first"], ["second"]]


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
