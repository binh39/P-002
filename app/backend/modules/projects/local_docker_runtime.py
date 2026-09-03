from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
import tomllib
from pathlib import Path
from typing import Any
from uuid import uuid4

from cloud.runtime_workspace import detect_layout, find_project_root, safe_extract_zip
from cloud.sandbox_builder import ArtifactManifest, RunnerIdentity
from cloud.sandbox_contract import (
    CoverageMode,
    DependencyPolicy,
    ResourceLimits,
    RunKind,
    RunnerProfile,
    RunSpec,
    SandboxSpec,
    SandboxStatus,
)
from cloud.sandbox_contract import (
    FailureStage as SandboxFailureStage,
)
from cloud.sandbox_dependency_plan import DependencyPlan, build_dependency_plan
from cloud.sandbox_executor import DockerExecutionRequest, DockerSandboxExecutor
from cloud.sandbox_runner_profiles import (
    SANDBOX_MANAGED_COVERAGE,
    SANDBOX_MANAGED_PYTEST,
    select_runner_profile,
)
from cloud.sandbox_security import bounded_redacted_text

from backend.infrastructure.storage import ObjectStorage

from .schemas import (
    MINIMUM_RUNTIME_PROTOCOL_VERSION,
    FailureStage,
    ProjectRecord,
    RuntimeProjectReport,
    RuntimeReport,
    RuntimeStatus,
)

_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_EXACT_REQUIREMENT = re.compile(
    r"^\s*([A-Za-z0-9_.-]+)(?:\[[^]]+\])?\s*==\s*([^\s,;]+)",
    re.IGNORECASE,
)
_SAFE_IMAGE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/@:-]{0,299}$")


class LocalDockerRuntimeError(RuntimeError):
    def __init__(
        self,
        error_code: str,
        message: str,
        *,
        stage: FailureStage = FailureStage.BUILD,
        retryable: bool = False,
    ):
        self.error_code = error_code
        self.stage = stage
        self.retryable = retryable
        super().__init__(message)


class LocalDockerRuntimePreparer:
    """Development-only project runtime backed by Docker Desktop.

    The API process stays on the host and invokes the already-versioned sandbox
    agent and executor. Uploaded source is mounted read-only, execution has no
    network, and the project environment is never merged with the optimizer.
    """

    job_name = "local-docker"

    def __init__(
        self,
        *,
        storage: ObjectStorage,
        image: str,
        root: Path,
        docker: str = "docker",
        command_runner=subprocess.run,
        health_ttl_seconds: float = 5.0,
    ):
        if not _SAFE_IMAGE.fullmatch(image):
            raise ValueError("Local sandbox image contains unsupported characters")
        self.storage = storage
        self.image = image
        self.root = root.resolve()
        self.docker = docker
        self.command_runner = command_runner
        self.health_ttl_seconds = health_ttl_seconds
        self.cache_root = self.root / "cache"
        self.jobs_root = self.root / "jobs"
        self.cache_root.mkdir(parents=True, exist_ok=True)
        self.jobs_root.mkdir(parents=True, exist_ok=True)
        if os.name != "nt":
            # These are dedicated sandbox exchange directories. The container
            # uses an unprivileged UID that intentionally differs from the host
            # CI/service UID and therefore needs explicit write permission.
            self.cache_root.chmod(0o777)
            self.jobs_root.chmod(0o777)
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._reports: dict[str, RuntimeReport] = {}
        self._health_checked_at = 0.0
        self._healthy = False
        self._image_digest: str | None = None
        self._contract: dict[str, Any] | None = None

    def is_healthy(self) -> bool:
        now = time.monotonic()
        if now - self._health_checked_at <= self.health_ttl_seconds:
            return self._healthy
        self._health_checked_at = now
        try:
            inspected = self.command_runner(
                [self.docker, "image", "inspect", "--format", "{{.Id}}", self.image],
                text=True,
                capture_output=True,
                timeout=10,
                check=False,
            )
            digest = (inspected.stdout or "").strip()
            if inspected.returncode != 0 or not _DIGEST.fullmatch(digest):
                raise RuntimeError((inspected.stderr or "Sandbox image is unavailable").strip())
            contracted = self.command_runner(
                [self.docker, "run", "--rm", digest, "contract"],
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
            if contracted.returncode != 0:
                raise RuntimeError((contracted.stderr or "Sandbox contract failed").strip())
            contract = json.loads((contracted.stdout or "").splitlines()[-1])
            if contract.get("python_minor") != "3.12" or contract.get("forbidden_modules_present"):
                raise RuntimeError("Sandbox image contract is incompatible")
            self._image_digest = digest
            self._contract = contract
            self._healthy = True
        except (OSError, RuntimeError, ValueError, IndexError, json.JSONDecodeError, subprocess.TimeoutExpired):
            self._healthy = False
            self._image_digest = None
            self._contract = None
        return self._healthy

    async def start(
        self,
        projects: list[ProjectRecord],
        *,
        reuse_bundle_object: str | None = None,
        expected_dependency_fingerprint: str | None = None,
    ) -> str:
        if len(projects) != 1:
            raise LocalDockerRuntimeError(
                "LOCAL_DOCKER_SINGLE_PROJECT_ONLY",
                "Local Docker mode creates one isolated environment per uploaded project",
                stage=FailureStage.METADATA,
            )
        if not await asyncio.to_thread(self.is_healthy):
            raise LocalDockerRuntimeError(
                "LOCAL_DOCKER_UNAVAILABLE",
                f"Docker Desktop or sandbox image {self.image!r} is unavailable",
                retryable=True,
            )
        prefix = f"local-runtime/{uuid4().hex}"
        snapshots = [ProjectRecord.model_validate(project.model_dump()) for project in projects]
        task = asyncio.create_task(
            self._prepare(
                prefix,
                snapshots[0],
                reuse_bundle_object=reuse_bundle_object,
                expected_dependency_fingerprint=expected_dependency_fingerprint,
            )
        )
        self._tasks[prefix] = task
        return prefix

    async def collect(self, prefix: str) -> RuntimeReport | None:
        task = self._tasks.get(prefix)
        if task is None:
            return self._reports.get(prefix)
        if not task.done():
            return None
        try:
            await task
        finally:
            self._tasks.pop(prefix, None)
        return self._reports.get(prefix)

    async def _prepare(
        self,
        prefix: str,
        project: ProjectRecord,
        *,
        reuse_bundle_object: str | None,
        expected_dependency_fingerprint: str | None,
    ) -> None:
        try:
            report = await self._prepare_project(
                prefix,
                project,
                reuse_bundle_object=reuse_bundle_object,
                expected_dependency_fingerprint=expected_dependency_fingerprint,
            )
        except Exception as exc:  # the polling API must always receive a terminal report
            report = self._failure_report(exc, project)
        self._reports[prefix] = report

    async def _prepare_project(
        self,
        prefix: str,
        project: ProjectRecord,
        *,
        reuse_bundle_object: str | None,
        expected_dependency_fingerprint: str | None,
    ) -> RuntimeReport:
        digest = self._image_digest
        contract = self._contract
        if digest is None or contract is None:
            raise LocalDockerRuntimeError("LOCAL_DOCKER_UNAVAILABLE", "Sandbox image health has expired")
        archive_bytes = await self.storage.read(project.object_name)
        with tempfile.TemporaryDirectory(prefix="promptopt-local-", dir=self.jobs_root) as temporary:
            workspace = Path(temporary)
            if os.name != "nt":
                workspace.chmod(0o755)
            source_archive = workspace / "project.zip"
            source_archive.write_bytes(archive_bytes)
            extracted = workspace / "source"
            safe_extract_zip(source_archive, extracted)
            project_root = find_project_root(extracted)
            source, tests = detect_layout(
                project_root,
                project.settings.runtime.source_directory,
                project.settings.tests.test_directory,
            )
            if not tests.is_dir():
                tests = project_root / ".promptopt-empty-tests"
                tests.mkdir()
            plan = build_dependency_plan(project_root)
            requested_python = project.settings.runtime.python_version
            if plan.python.python_version != requested_python:
                raise LocalDockerRuntimeError(
                    "INCOMPATIBLE_PYTHON",
                    f"Project metadata resolves Python {plan.python.python_version}, requested {requested_python}",
                    stage=FailureStage.METADATA,
                )
            runner = self._runner_identity(project_root, plan)
            if reuse_bundle_object:
                artifact, manifest = await self._restore_artifact(
                    workspace,
                    reuse_bundle_object,
                    expected_dependency_fingerprint,
                    digest,
                    plan,
                )
            else:
                artifact, manifest = await self._build_artifact(project_root, plan, digest, runner)
            bundle_object = f"local-runtime/artifacts/{manifest.fingerprint}/environment.tar.gz"
            manifest_object = self._manifest_object(bundle_object)
            await self.storage.write(bundle_object, artifact.read_bytes(), "application/gzip")
            await self.storage.write(
                manifest_object,
                json.dumps(manifest.as_dict(), sort_keys=True, separators=(",", ":")).encode(),
                "application/json",
            )
            result = await self._execute(
                project,
                project_root=project_root,
                source=source,
                tests=tests,
                plan=plan,
                artifact=artifact,
                manifest_path=artifact.with_name("manifest.json"),
                manifest=manifest,
                output_root=workspace / "output",
                archive_sha256=hashlib.sha256(archive_bytes).hexdigest(),
                bundle_object=bundle_object,
            )
            return result

    async def _build_artifact(
        self,
        project_root: Path,
        plan: DependencyPlan,
        digest: str,
        runner: RunnerIdentity,
    ) -> tuple[Path, ArtifactManifest]:
        plan_path = project_root / ".promptopt-dependency-plan.json"
        plan_path.write_text(json.dumps(plan.canonical_dict(), sort_keys=True), encoding="utf-8")
        command = [
            self.docker,
            "run",
            "--rm",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--cpus",
            "2",
            "--memory",
            "4096m",
            "--memory-swap",
            "4096m",
            "--pids-limit",
            "256",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,nodev,size=268435456",
            "--env",
            "UV_CACHE_DIR=/cache/uv",
            "--mount",
            self._mount(project_root, "/project", readonly=True),
            "--mount",
            self._mount(self.cache_root, "/cache"),
            digest,
            "build",
            "--project-root",
            "/project",
            "--plan",
            "/project/.promptopt-dependency-plan.json",
            "--cache-root",
            "/cache",
            "--image-digest",
            digest,
            "--runner-profile",
            runner.profile,
            "--pytest-version",
            runner.pytest_version,
            "--coverage-version",
            runner.coverage_version,
        ]
        try:
            completed = await asyncio.to_thread(
                self.command_runner,
                command,
                text=True,
                capture_output=True,
                timeout=1800,
                check=False,
            )
        finally:
            plan_path.unlink(missing_ok=True)
        if completed.returncode != 0:
            diagnostic = bounded_redacted_text(
                "\n".join(part for part in (completed.stdout, completed.stderr) if part) or "Local Docker build failed",
                4000,
            )
            lowered = diagnostic.casefold()
            if "no solution found" in lowered or "unsatisfiable" in lowered or "dependency conflict" in lowered:
                raise LocalDockerRuntimeError(
                    "DEPENDENCY_CONFLICT",
                    diagnostic,
                    stage=FailureStage.RESOLVE,
                )
            raise LocalDockerRuntimeError(
                "LOCAL_DOCKER_BUILD_FAILED",
                diagnostic,
                stage=FailureStage.RESOLVE,
                retryable=True,
            )
        try:
            payload = json.loads([line for line in completed.stdout.splitlines() if line.strip()][-1])
            fingerprint = str(payload["fingerprint"])
        except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise LocalDockerRuntimeError(
                "LOCAL_DOCKER_BUILD_PROTOCOL",
                "Sandbox builder returned an invalid response",
                retryable=True,
            ) from exc
        object_root = self.cache_root / "objects" / fingerprint
        artifact = object_root / "environment.tar.gz"
        manifest_path = object_root / "manifest.json"
        try:
            manifest = ArtifactManifest.from_dict(json.loads(manifest_path.read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            raise LocalDockerRuntimeError(
                "LOCAL_DOCKER_ARTIFACT_INVALID",
                "Sandbox builder did not publish a valid immutable artifact",
                retryable=True,
            ) from exc
        return artifact, manifest

    async def _restore_artifact(
        self,
        workspace: Path,
        bundle_object: str,
        expected_fingerprint: str | None,
        image_digest: str,
        plan: DependencyPlan,
    ) -> tuple[Path, ArtifactManifest]:
        artifact = workspace / "environment.tar.gz"
        manifest_path = workspace / "manifest.json"
        artifact.write_bytes(await self.storage.read(bundle_object))
        manifest_path.write_bytes(await self.storage.read(self._manifest_object(bundle_object)))
        manifest = ArtifactManifest.from_dict(json.loads(manifest_path.read_text(encoding="utf-8")))
        if not expected_fingerprint or manifest.fingerprint != expected_fingerprint:
            raise LocalDockerRuntimeError(
                "ENVIRONMENT_FINGERPRINT_MISMATCH",
                "Reusable environment fingerprint does not match the active project",
            )
        if manifest.image.image_digest != image_digest or manifest.dependency_plan_fingerprint != plan.fingerprint:
            raise LocalDockerRuntimeError(
                "ENVIRONMENT_FINGERPRINT_MISMATCH",
                "Project source, dependencies, or sandbox image changed before execution retry",
            )
        return artifact, manifest

    async def _execute(
        self,
        project: ProjectRecord,
        *,
        project_root: Path,
        source: Path,
        tests: Path,
        plan: DependencyPlan,
        artifact: Path,
        manifest_path: Path,
        manifest: ArtifactManifest,
        output_root: Path,
        archive_sha256: str,
        bundle_object: str,
    ) -> RuntimeReport:
        source_relative = source.relative_to(project_root).as_posix() or "."
        tests_relative = tests.relative_to(project_root).as_posix() or "."
        spec = SandboxSpec(
            project_id=project.id,
            archive_sha256=archive_sha256,
            requested_python=project.settings.runtime.python_version,
            detected_python=plan.python.python_version,
            source_directory=source_relative,
            test_directory=tests_relative,
            dependency_policy=DependencyPolicy(
                mode=plan.mode,
                manifest=plan.manifest,
                lock_file=plan.lock_file,
                groups=plan.groups,
                extras=plan.extras,
                package_index_refs=plan.package_index_refs,
            ),
            runner_profile=RunnerProfile(manifest.runner.profile),
            coverage_mode=(
                CoverageMode.STATEMENT_AND_BRANCH
                if project.settings.coverage.branch_enabled
                else CoverageMode.STATEMENT
            ),
            allowed_environment_variables=("LANG", "LC_ALL", "PYTHONHASHSEED", "TZ"),
            resource_limits=ResourceLimits(
                cpu=project.settings.runtime.cpu,
                memory_mb=project.settings.runtime.memory_mb,
                timeout_seconds=project.settings.runtime.run_timeout_seconds,
                maximum_processes=128,
                maximum_output_bytes=project.settings.security.maximum_output_bytes,
            ),
        )
        run_spec = RunSpec(
            run_id=f"local-{uuid4().hex}",
            kind=RunKind.BASELINE,
            environment_fingerprint=manifest.fingerprint,
            test_paths=(tests_relative,),
            test_pattern=project.settings.tests.test_pattern,
        )
        executor = DockerSandboxExecutor(docker=self.docker, runner=self.command_runner)
        result = await asyncio.to_thread(
            executor.execute,
            DockerExecutionRequest(
                image_digest=manifest.image.image_digest,
                artifact_archive=artifact,
                artifact_manifest=manifest_path,
                source_root=project_root,
                output_root=output_root,
                sandbox_spec=spec,
                run_spec=run_spec,
                environment={"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PYTHONHASHSEED": "0", "TZ": "UTC"},
            ),
        )
        project_report = RuntimeProjectReport(
            source_directory=source_relative,
            test_directory=tests_relative,
            dependency_files=[item for item in (plan.manifest, plan.lock_file) if item],
            collected_tests=result.test_counts.collected,
            statement_coverage=self._ratio(
                result.coverage.covered_statements if result.coverage else 0,
                result.coverage.total_statements if result.coverage else 0,
            ),
            branch_coverage=self._ratio(
                result.coverage.covered_branches if result.coverage else 0,
                result.coverage.total_branches if result.coverage else 0,
            ),
        )
        common = {
            "projects": {project.id: project_report},
            "dependency_fingerprint": manifest.fingerprint,
            "environment_fingerprint": manifest.fingerprint,
            "requested_python_version": project.settings.runtime.python_version,
            "detected_python_version": plan.python.python_version,
            "resolved_python_version": manifest.image.python_minor,
            "runner_profile": result.runner_profile.value if result.runner_profile else manifest.runner.profile,
            "pytest_version": result.pytest_version or manifest.runner.pytest_version,
            "coverage_version": result.coverage_version or manifest.runner.coverage_version,
            "bundle_object": bundle_object,
            "protocol_version": MINIMUM_RUNTIME_PROTOCOL_VERSION,
        }
        if result.status is SandboxStatus.FAILED:
            return RuntimeReport(
                status=RuntimeStatus.FAILED,
                error=bounded_redacted_text(
                    "\n".join(part for part in (result.stdout, result.stderr) if part)
                    or result.error_code
                    or "Sandbox execution failed",
                    4000,
                ),
                failure_stage=self._failure_stage(result.failure_stage),
                error_code=result.error_code or "LOCAL_DOCKER_EXECUTION_FAILED",
                retryable=result.retryable,
                **common,
            )
        return RuntimeReport(
            status=RuntimeStatus.READY,
            source_directory=source_relative,
            test_directory=tests_relative,
            dependency_files=project_report.dependency_files,
            install_strategy="isolated Docker artifact per environment fingerprint",
            collected_tests=result.test_counts.collected,
            statement_coverage=project_report.statement_coverage,
            branch_coverage=project_report.branch_coverage,
            **common,
        )

    def _runner_identity(self, project_root: Path, plan: DependencyPlan) -> RunnerIdentity:
        versions = self._locked_versions(project_root, plan)
        declared_names: set[str] = set()
        for requirement in plan.declared_requirements:
            if match := _EXACT_REQUIREMENT.match(requirement):
                name = self._package_name(match.group(1))
                declared_names.add(name)
                versions.setdefault(name, match.group(2))
                continue
            name = self._package_name(re.split(r"[<>=!~;\s\[]", requirement, maxsplit=1)[0])
            if name:
                declared_names.add(name)
        unresolved = {name for name in ("pytest", "coverage") if name in declared_names and name not in versions}
        if unresolved:
            raise LocalDockerRuntimeError(
                "LOCAL_RUNNER_IDENTITY_UNRESOLVED",
                "Local Docker mode requires a lock file or exact pins for project-native pytest/coverage: "
                + ", ".join(sorted(unresolved)),
                stage=FailureStage.METADATA,
            )
        decision = select_runner_profile(versions)
        if decision.error_code:
            raise LocalDockerRuntimeError(
                decision.error_code,
                decision.reason,
                stage=FailureStage.METADATA,
            )
        return RunnerIdentity(
            profile=decision.profile.value,
            pytest_version=decision.pytest_version or SANDBOX_MANAGED_PYTEST,
            coverage_version=decision.coverage_version or SANDBOX_MANAGED_COVERAGE,
        )

    @staticmethod
    def _locked_versions(project_root: Path, plan: DependencyPlan) -> dict[str, str]:
        if not plan.lock_file:
            return {}
        try:
            payload = tomllib.loads((project_root / plan.lock_file).read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            return {}
        packages = payload.get("package", [])
        if not isinstance(packages, list):
            return {}
        versions: dict[str, str] = {}
        for package in packages:
            if not isinstance(package, dict) or not isinstance(package.get("name"), str):
                continue
            version = package.get("version")
            if isinstance(version, str):
                versions[LocalDockerRuntimePreparer._package_name(package["name"])] = version
        return versions

    def _failure_report(self, exc: Exception, project: ProjectRecord) -> RuntimeReport:
        if isinstance(exc, LocalDockerRuntimeError):
            stage = exc.stage
            code = exc.error_code
            retryable = exc.retryable
        elif isinstance(exc, subprocess.TimeoutExpired):
            stage, code, retryable = FailureStage.BUILD, "LOCAL_DOCKER_TIMEOUT", True
        else:
            stage, code, retryable = FailureStage.INTERNAL, "LOCAL_DOCKER_INTERNAL", True
        return RuntimeReport(
            status=RuntimeStatus.FAILED,
            error=bounded_redacted_text(str(exc), 4000),
            failure_stage=stage,
            error_code=code,
            retryable=retryable,
            requested_python_version=project.settings.runtime.python_version,
            protocol_version=MINIMUM_RUNTIME_PROTOCOL_VERSION,
        )

    @staticmethod
    def _failure_stage(stage: SandboxFailureStage | None) -> FailureStage:
        return {
            SandboxFailureStage.COLLECT: FailureStage.COLLECT,
            SandboxFailureStage.TEST: FailureStage.TEST,
            SandboxFailureStage.COVERAGE: FailureStage.COVERAGE,
            SandboxFailureStage.TIMEOUT: FailureStage.TEST,
            SandboxFailureStage.BUILD: FailureStage.BUILD,
            SandboxFailureStage.INTERNAL: FailureStage.INTERNAL,
            None: FailureStage.INTERNAL,
        }[stage]

    @staticmethod
    def _manifest_object(bundle_object: str) -> str:
        return f"{bundle_object}.manifest.json"

    @staticmethod
    def _ratio(covered: int, total: int) -> float | None:
        return covered / total if total else None

    @staticmethod
    def _package_name(value: str) -> str:
        return value.strip().lower().replace("_", "-").replace(".", "-")

    @staticmethod
    def _mount(source: Path, target: str, *, readonly: bool = False) -> str:
        resolved = str(source.resolve())
        if "," in resolved:
            raise LocalDockerRuntimeError(
                "LOCAL_DOCKER_PATH_UNSUPPORTED",
                "Local Docker workspace paths cannot contain commas",
                stage=FailureStage.METADATA,
            )
        suffix = ",readonly" if readonly else ""
        return f"type=bind,source={resolved},target={target}{suffix}"
