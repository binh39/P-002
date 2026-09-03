from datetime import UTC, datetime

import pytest

from backend.modules.projects.rollout import (
    RolloutMode,
    RolloutPolicy,
    RuntimeRolloutMetrics,
    RuntimeRolloutPreparer,
    parse_runtime_report,
)
from backend.modules.projects.schemas import (
    ProjectRecord,
    ProjectSettings,
    ProjectStatus,
    RuntimeReport,
    RuntimeStatus,
)


def project(project_id: str = "candidate", python: str = "3.12") -> ProjectRecord:
    now = datetime.now(UTC)
    settings = ProjectSettings()
    settings.runtime.python_version = python
    return ProjectRecord(
        id=project_id,
        owner_id="owner",
        name=project_id,
        description="",
        upload_id="upload",
        object_name="uploads/project.zip",
        branch="main",
        commit=None,
        status=ProjectStatus.READY,
        settings=settings,
        created_at=now,
        updated_at=now,
    )


class FakeRunner:
    def __init__(self, name: str, report: RuntimeReport, *, start_error: Exception | None = None):
        self.name = name
        self.report = report
        self.start_error = start_error
        self.starts = 0

    async def start(self, projects, **options):
        del projects, options
        self.starts += 1
        if self.start_error:
            raise self.start_error
        return f"{self.name}/execution"

    async def collect(self, prefix):
        assert prefix == f"{self.name}/execution"
        return self.report

    def is_healthy(self):
        return True


def ready(bundle: str, *, tests: int = 1, protocol: int = 8) -> RuntimeReport:
    return RuntimeReport(
        status=RuntimeStatus.READY,
        bundle_object=bundle,
        collected_tests=tests,
        protocol_version=protocol,
    )


def test_dual_read_accepts_legacy_v8_and_sandbox_v1():
    legacy = parse_runtime_report(
        {
            "status": "runtime_ready",
            "bundle_object": "legacy/runtime.tar.gz",
            "protocol_version": 8,
            "project_root": "/must/not/leak",
        }
    )
    sandbox = parse_runtime_report(
        {
            "status": "succeeded",
            "run_id": "sandbox-run",
            "environment_fingerprint": "a" * 64,
            "test_counts": {"collected": 2, "passed": 2, "failed": 0, "skipped": 0},
            "coverage": {
                "covered_statements": 3,
                "total_statements": 4,
                "covered_branches": 1,
                "total_branches": 2,
            },
            "protocol_version": 1,
        }
    )

    assert legacy.status is RuntimeStatus.READY
    assert legacy.bundle_object == "legacy/runtime.tar.gz"
    assert legacy.protocol_version == 8
    assert sandbox.status is RuntimeStatus.READY
    assert sandbox.collected_tests == 2
    assert sandbox.statement_coverage == 0.75
    assert sandbox.branch_coverage == 0.5
    assert sandbox.protocol_version == 1


@pytest.mark.asyncio
async def test_shadow_runs_both_but_only_returns_legacy_for_activation():
    legacy = FakeRunner("legacy", ready("legacy/active.tar.gz"))
    sandbox = FakeRunner("sandbox", ready("sandbox/shadow.tar.gz"))
    metrics = RuntimeRolloutMetrics()
    rollout = RuntimeRolloutPreparer(
        legacy,
        sandbox,
        RolloutPolicy(enabled=True, mode=RolloutMode.SHADOW),
        metrics=metrics,
        clock=lambda: 10.0,
    )

    candidate = project()
    candidate.runtime_bundle_object = "legacy/active-before-shadow.tar.gz"
    token = await rollout.start([candidate])
    report = await rollout.collect(token)

    assert legacy.starts == 1
    assert sandbox.starts == 1
    assert report.bundle_object == "legacy/active.tar.gz"
    assert candidate.runtime_bundle_object == "legacy/active-before-shadow.tar.gz"
    assert metrics.shadow_matches == 1
    assert metrics.completions == {"shadow": 1}


@pytest.mark.asyncio
async def test_shadow_start_failure_never_blocks_legacy_activation():
    legacy = FakeRunner("legacy", ready("legacy/active.tar.gz"))
    sandbox = FakeRunner("sandbox", ready("sandbox/unused.tar.gz"), start_error=RuntimeError("offline"))
    metrics = RuntimeRolloutMetrics()
    rollout = RuntimeRolloutPreparer(
        legacy,
        sandbox,
        RolloutPolicy(enabled=True, mode=RolloutMode.SHADOW),
        metrics=metrics,
    )

    report = await rollout.collect(await rollout.start([project()]))

    assert report.bundle_object == "legacy/active.tar.gz"
    assert metrics.shadow_start_failures == 1
    assert metrics.shadow_mismatches == 1


def test_canary_route_is_stable_and_python_allowlisted():
    policy = RolloutPolicy(
        enabled=True,
        mode=RolloutMode.CANARY,
        canary_percent=50,
        canary_python_versions=frozenset({"3.12"}),
    )

    first = policy.route(project("stable-project"))

    assert first in {"legacy", "sandbox"}
    assert policy.route(project("stable-project")) == first
    assert policy.route(project("python-311", python="3.11")) == "legacy"


def test_disabling_feature_flag_is_an_immediate_legacy_rollback():
    policy = RolloutPolicy(
        enabled=False,
        mode=RolloutMode.ENABLED,
        canary_percent=100,
    )

    candidate = project()
    candidate.runtime_bundle_object = "runtime/active-before-rollback.tar.gz"

    assert policy.route(candidate) == "legacy"
    assert candidate.runtime_bundle_object == "runtime/active-before-rollback.tar.gz"
