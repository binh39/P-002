import json
import os
import subprocess
import tarfile
from pathlib import Path, PurePosixPath
from types import SimpleNamespace

import pytest

from cloud.sandbox_builder import (
    ArtifactManifest,
    CacheMetrics,
    CachePolicy,
    EnvironmentArtifactBuilder,
    FileArtifactCache,
    ImageIdentity,
    PackageRecord,
    RetryPolicy,
    RunnerIdentity,
    SandboxBuildError,
    UvProjectResolver,
    environment_fingerprint,
)
from cloud.sandbox_dependency_plan import DependencyPlan, DependencySelection, build_dependency_plan

CATALOG = json.loads((Path(__file__).parent / "fixtures" / "sandbox_projects.json").read_text(encoding="utf-8"))
IMAGE = ImageIdentity(
    python_minor="3.12",
    python_full_version="3.12.14",
    platform="linux",
    architecture="x86_64",
    image_digest="sha256:" + "1" * 64,
)
RUNNER = RunnerIdentity(profile="project_native", pytest_version="9.1.1", coverage_version="7.15.2")


def materialize(case_name: str, root: Path) -> Path:
    root.mkdir(parents=True)
    for relative, content in CATALOG[case_name]["files"].items():
        destination = root / PurePosixPath(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
    return root


class FakeResolver:
    def __init__(self, *, packages=(PackageRecord("coverage", "7.10.7"),), failures=()):
        self.packages = tuple(packages)
        self.failures = list(failures)
        self.resolve_calls = 0
        self.check_calls = 0

    def resolve(self, project_root, plan, venv_dir, *, network_allowed):
        del project_root, plan
        self.resolve_calls += 1
        assert network_allowed is True
        if self.failures:
            raise self.failures.pop(0)
        python = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        python.parent.mkdir(parents=True)
        python.write_bytes(b"sandbox-python")
        site = venv_dir / "site-packages"
        site.mkdir()
        for package in self.packages:
            (site / f"{package.name}-{package.version}.dist-info").mkdir()

    def check(self, venv_dir):
        assert venv_dir.is_dir()
        self.check_calls += 1

    def inventory(self, venv_dir):
        assert venv_dir.is_dir()
        return self.packages


def builder(tmp_path, resolver, **kwargs):
    cache = FileArtifactCache(tmp_path / "cache", metrics=CacheMetrics())
    return EnvironmentArtifactBuilder(cache, resolver, **kwargs), cache


def test_isort_style_coverage_pin_builds_without_optimizer_bundle(tmp_path):
    project = materialize("coverage_7_10_7", tmp_path / "project")
    plan = build_dependency_plan(project)
    resolver = FakeResolver()
    service, _ = builder(tmp_path, resolver)

    artifact = service.build(project, plan, IMAGE, RUNNER)

    assert resolver.resolve_calls == 1
    assert PackageRecord("coverage", "7.10.7") in artifact.manifest.inventory
    assert artifact.manifest.runner.coverage_version == "7.15.2"
    assert artifact.manifest.inventory_sha256


def test_cache_hit_skips_resolver_and_records_metrics(tmp_path):
    project = materialize("py312_minimal", tmp_path / "project")
    plan = build_dependency_plan(project)
    resolver = FakeResolver()
    service, cache = builder(tmp_path, resolver)

    first = service.build(project, plan, IMAGE, RUNNER)
    second = service.build(project, plan, IMAGE, RUNNER)

    assert first.directory == second.directory
    assert resolver.resolve_calls == 1
    assert cache.metrics.misses == 1
    assert cache.metrics.hits == 1
    assert cache.metrics.publishes == 1
    assert len(cache.metrics.build_duration_seconds) == 1


def test_conflicting_projects_create_independent_artifacts(tmp_path):
    first_project = materialize("conflict_v1", tmp_path / "first")
    second_project = materialize("conflict_v2", tmp_path / "second")
    service, _ = builder(tmp_path, FakeResolver())

    first = service.build(first_project, build_dependency_plan(first_project), IMAGE, RUNNER)
    second = service.build(second_project, build_dependency_plan(second_project), IMAGE, RUNNER)

    assert first.manifest.fingerprint != second.manifest.fingerprint
    assert first.directory.is_dir() and second.directory.is_dir()


def test_failed_build_is_not_published_and_keeps_good_artifact(tmp_path):
    good_project = materialize("py312_minimal", tmp_path / "good")
    bad_project = materialize("conflict_v1", tmp_path / "bad")
    resolver = FakeResolver()
    service, cache = builder(tmp_path, resolver)
    good = service.build(good_project, build_dependency_plan(good_project), IMAGE, RUNNER)
    good_hash = good.manifest.artifact_sha256
    resolver.failures.append(SandboxBuildError("DEPENDENCY_CONFLICT", "unsatisfiable", retryable=False))

    with pytest.raises(SandboxBuildError, match="unsatisfiable"):
        service.build(bad_project, build_dependency_plan(bad_project), IMAGE, RUNNER)

    assert cache.get(good.manifest.fingerprint).manifest.artifact_sha256 == good_hash
    bad_fingerprint = environment_fingerprint(build_dependency_plan(bad_project), IMAGE, RUNNER)
    assert not (cache.objects / bad_fingerprint).exists()
    assert not any(cache.staging.iterdir())


def test_archive_contains_only_environment_not_project_source_or_secret(tmp_path):
    project = materialize("py312_minimal", tmp_path / "project")
    (project / ".env").write_text("TOKEN=secret", encoding="utf-8")
    service, _ = builder(tmp_path, FakeResolver())

    artifact = service.build(project, build_dependency_plan(project), IMAGE, RUNNER)

    with tarfile.open(artifact.archive, "r:gz") as archive:
        names = archive.getnames()
        assert names and all(name == "venv" or name.startswith("venv/") for name in names)
        assert not any(".env" in name or "test_minimal.py" in name for name in names)


def test_corrupt_cache_is_quarantined_and_rebuilt(tmp_path):
    project = materialize("py312_minimal", tmp_path / "project")
    plan = build_dependency_plan(project)
    resolver = FakeResolver()
    service, cache = builder(tmp_path, resolver)
    artifact = service.build(project, plan, IMAGE, RUNNER)
    artifact.archive.write_bytes(b"corrupt")

    rebuilt = service.build(project, plan, IMAGE, RUNNER)

    assert resolver.resolve_calls == 2
    assert cache.metrics.corruptions == 1
    assert rebuilt.manifest.artifact_sha256 != "corrupt"
    assert any(cache.quarantine.iterdir())


def test_tampered_inventory_metadata_is_quarantined_and_rebuilt(tmp_path):
    project = materialize("py312_minimal", tmp_path / "project")
    plan = build_dependency_plan(project)
    resolver = FakeResolver()
    service, cache = builder(tmp_path, resolver)
    artifact = service.build(project, plan, IMAGE, RUNNER)
    manifest_path = artifact.directory / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["inventory"][0]["version"] = "tampered"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    service.build(project, plan, IMAGE, RUNNER)

    assert resolver.resolve_calls == 2
    assert cache.metrics.corruptions == 1


def test_lease_rejects_second_worker_for_same_fingerprint(tmp_path):
    cache = FileArtifactCache(tmp_path / "cache")
    fingerprint = "a" * 64

    with cache.acquire(fingerprint):
        with pytest.raises(SandboxBuildError) as caught:
            cache.acquire(fingerprint)

    assert caught.value.error_code == "ARTIFACT_BUILD_IN_PROGRESS"
    assert caught.value.retryable is True
    assert cache.metrics.lease_contentions == 1


def test_gc_honors_ttl_quota_and_pins(tmp_path):
    now = [100]
    cache = FileArtifactCache(
        tmp_path / "cache",
        policy=CachePolicy(ttl_seconds=10, quota_bytes=1, lease_seconds=10),
        clock=lambda: now[0],
    )
    project = materialize("py312_minimal", tmp_path / "project")
    plan = build_dependency_plan(project)
    service = EnvironmentArtifactBuilder(cache, FakeResolver(), clock=lambda: now[0])
    artifact = service.build(project, plan, IMAGE, RUNNER)
    now[0] = 200

    assert cache.collect_garbage(pinned={artifact.manifest.fingerprint}) == ()
    assert cache.collect_garbage() == (artifact.manifest.fingerprint,)
    assert cache.metrics.evictions == 1


def test_only_transient_failures_retry_with_exponential_backoff(tmp_path):
    project = materialize("py312_minimal", tmp_path / "project")
    transient = SandboxBuildError("DEPENDENCY_NETWORK_TRANSIENT", "network", retryable=True)
    resolver = FakeResolver(failures=(transient, transient))
    delays = []
    service, cache = builder(
        tmp_path,
        resolver,
        retry_policy=RetryPolicy(
            maximum_attempts=3, base_delay_seconds=1, maximum_delay_seconds=9, deadline_seconds=20
        ),
        sleep=delays.append,
        random_source=lambda: 0.5,
    )

    service.build(project, build_dependency_plan(project), IMAGE, RUNNER)

    assert resolver.resolve_calls == 3
    assert delays == [1, 2]
    assert cache.metrics.retry_count == 2


@pytest.mark.parametrize("code", ["DEPENDENCY_CONFLICT", "INCOMPATIBLE_PYTHON"])
def test_non_retryable_resolution_failures_stop_immediately(tmp_path, code):
    project = materialize("py312_minimal", tmp_path / "project")
    resolver = FakeResolver(failures=(SandboxBuildError(code, "permanent", retryable=False),))
    service, cache = builder(tmp_path, resolver, sleep=lambda _: pytest.fail("must not sleep"))

    with pytest.raises(SandboxBuildError) as caught:
        service.build(project, build_dependency_plan(project), IMAGE, RUNNER)

    assert caught.value.error_code == code
    assert resolver.resolve_calls == 1
    assert cache.metrics.retry_count == 0


def test_retry_deadline_prevents_another_attempt(tmp_path):
    project = materialize("py312_minimal", tmp_path / "project")
    transient = SandboxBuildError("DEPENDENCY_RESOLUTION_TIMEOUT", "timeout", retryable=True)
    resolver = FakeResolver(failures=(transient,))
    service, _ = builder(
        tmp_path,
        resolver,
        retry_policy=RetryPolicy(maximum_attempts=3, base_delay_seconds=2, maximum_delay_seconds=2, deadline_seconds=1),
        random_source=lambda: 0.5,
    )

    with pytest.raises(SandboxBuildError) as caught:
        service.build(project, build_dependency_plan(project), IMAGE, RUNNER)

    assert caught.value.error_code == "DEPENDENCY_RETRY_DEADLINE"
    assert resolver.resolve_calls == 1


def test_image_digest_and_runner_are_part_of_fingerprint(tmp_path):
    project = materialize("py312_minimal", tmp_path / "project")
    plan = build_dependency_plan(project)
    second_image = ImageIdentity("3.12", "3.12.14", "linux", "x86_64", "sha256:" + "2" * 64)
    second_runner = RunnerIdentity("project_native", "9.1.1", "7.10.7")

    base = environment_fingerprint(plan, IMAGE, RUNNER)

    assert base != environment_fingerprint(plan, second_image, RUNNER)
    assert base != environment_fingerprint(plan, IMAGE, second_runner)


def test_builder_rejects_wrong_routed_python_image(tmp_path):
    project = materialize("py312_minimal", tmp_path / "project")
    wrong = ImageIdentity("3.13", "3.13.7", "linux", "x86_64", "sha256:" + "3" * 64)
    service, _ = builder(tmp_path, FakeResolver())

    with pytest.raises(SandboxBuildError) as caught:
        service.build(project, build_dependency_plan(project), wrong, RUNNER)

    assert caught.value.error_code == "INCOMPATIBLE_PYTHON"


def test_resolver_preserves_manifest_source_on_conflict(tmp_path):
    def failed_runner(*args, **kwargs):
        del args, kwargs
        return SimpleNamespace(
            returncode=1,
            stdout="Because coverage==7.15.2 and coverage==7.10.7, requirements are unsatisfiable",
        )

    resolver = UvProjectResolver(runner=failed_runner)

    with pytest.raises(SandboxBuildError) as caught:
        resolver._run(
            ["uv", "pip", "install"],
            cwd=tmp_path,
            network_allowed=True,
            sources=("pyproject.toml",),
        )

    assert caught.value.error_code == "DEPENDENCY_CONFLICT"
    assert caught.value.sources == ("pyproject.toml",)
    assert "coverage==7.10.7" in str(caught.value)


def test_subprocess_timeout_is_retryable_and_keeps_source(tmp_path):
    def timed_out(*args, **kwargs):
        del args, kwargs
        raise subprocess.TimeoutExpired("uv", 900)

    resolver = UvProjectResolver(runner=timed_out)

    with pytest.raises(SandboxBuildError) as caught:
        resolver._run(["uv", "pip", "install"], cwd=tmp_path, network_allowed=True, sources=("uv.lock",))

    assert caught.value.error_code == "DEPENDENCY_RESOLUTION_TIMEOUT"
    assert caught.value.retryable is True
    assert caught.value.sources == ("uv.lock",)


def test_inventory_parses_stdout_without_uv_status_from_stderr(tmp_path):
    def listed(*args, **kwargs):
        del args, kwargs
        return SimpleNamespace(
            returncode=0,
            stdout='[{"name":"coverage","version":"7.10.7"}]',
            stderr="Using Python 3.12 environment at: /cache/staging/venv",
        )

    inventory = UvProjectResolver(runner=listed).inventory(tmp_path / "venv")

    assert inventory == (PackageRecord("coverage", "7.10.7"),)


def test_manifest_round_trip_and_inventory_hash_validation(tmp_path):
    project = materialize("py312_minimal", tmp_path / "project")
    service, _ = builder(tmp_path, FakeResolver())
    artifact = service.build(project, build_dependency_plan(project), IMAGE, RUNNER)

    restored = ArtifactManifest.from_dict(artifact.manifest.as_dict())

    assert restored == artifact.manifest
    assert restored.inventory_sha256


def test_dependency_plan_round_trip_rejects_tampering(tmp_path):
    project = materialize("py312_minimal", tmp_path / "project")
    plan = build_dependency_plan(project)

    assert DependencyPlan.from_dict(plan.canonical_dict()) == plan
    tampered = plan.canonical_dict()
    tampered["groups"] = ["release"]
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        DependencyPlan.from_dict(tampered)


def test_package_index_refs_are_mapped_to_environment_and_redacted(tmp_path):
    project = materialize("py312_minimal", tmp_path / "project")
    plan = build_dependency_plan(project, DependencySelection(package_index_refs=("private",)))
    calls = []

    def runner(command, **kwargs):
        calls.append((command, kwargs["env"]))
        if command[1:2] == ["venv"]:
            python = Path(command[-1]) / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            python.parent.mkdir(parents=True)
            python.write_bytes(b"python")
            return SimpleNamespace(returncode=0, stdout="")
        if "install" in command:
            return SimpleNamespace(returncode=1, stdout="download failed from https://user:secret@index.example/simple")
        return SimpleNamespace(returncode=0, stdout="[]")

    resolver = UvProjectResolver(
        index_urls={"private": "https://user:secret@index.example/simple"},
        runner=runner,
    )

    with pytest.raises(SandboxBuildError) as caught:
        resolver.resolve(project, plan, tmp_path / "venv", network_allowed=True)

    install_environment = next(environment for command, environment in calls if "install" in command)
    assert install_environment["UV_INDEX_URL"] == "https://user:secret@index.example/simple"
    assert "secret" not in str(caught.value)
    assert "<redacted-package-index>" in str(caught.value)


def test_unconfigured_package_index_reference_fails_without_secret(tmp_path):
    project = materialize("py312_minimal", tmp_path / "project")
    plan = build_dependency_plan(project, DependencySelection(package_index_refs=("private",)))

    with pytest.raises(SandboxBuildError) as caught:
        UvProjectResolver(runner=lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="")).resolve(
            project,
            plan,
            tmp_path / "venv",
            network_allowed=True,
        )

    assert caught.value.error_code == "PACKAGE_INDEX_NOT_CONFIGURED"
    assert caught.value.sources == ("private",)


def test_sandbox_dockerfile_is_minimal_and_version_parameterized():
    dockerfile = (Path(__file__).parents[1] / "cloud" / "Dockerfile.sandbox").read_text(encoding="utf-8")

    assert "ARG PYTHON_VERSION=3.12" in dockerfile
    assert "python:${PYTHON_VERSION}-slim-bookworm" in dockerfile
    for forbidden in ("coverup", "dspy", "gepa", "litellm", "openai"):
        assert forbidden not in dockerfile.casefold()
