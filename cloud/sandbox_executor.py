"""Host-side Docker launcher for isolated project test executions."""

from __future__ import annotations

import json
import os
import re
import subprocess
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from cloud.sandbox_builder import ArtifactManifest
from cloud.sandbox_contract import RunSpec, SandboxResult, SandboxSpec

_IMAGE_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_SAFE_ENVIRONMENT = frozenset({"LANG", "LC_ALL", "PYTHONHASHSEED", "TZ"})


class SandboxExecutorError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DockerExecutionRequest:
    image_digest: str
    artifact_archive: Path
    artifact_manifest: Path
    source_root: Path
    output_root: Path
    sandbox_spec: SandboxSpec
    run_spec: RunSpec
    tests_root: Path | None = None
    environment: dict[str, str] = field(default_factory=dict)


class DockerSandboxExecutor:
    def __init__(self, *, docker: str = "docker", runner=None):
        self.docker = docker
        self.runner = runner or subprocess.run

    def build_command(
        self,
        request: DockerExecutionRequest,
        *,
        spec_path: Path,
        run_path: Path,
        container_name: str | None = None,
    ) -> list[str]:
        if not _IMAGE_DIGEST.fullmatch(request.image_digest):
            raise SandboxExecutorError("Execution image must be pinned by sha256 digest")
        for path, label in (
            (request.artifact_archive, "artifact archive"),
            (request.artifact_manifest, "artifact manifest"),
            (request.source_root, "source root"),
            (request.tests_root or request.source_root, "generated tests root"),
            (spec_path, "SandboxSpec"),
            (run_path, "RunSpec"),
        ):
            if not path.resolve().exists():
                raise SandboxExecutorError(f"Missing {label}: {path}")
        request.output_root.resolve().mkdir(parents=True, exist_ok=True)
        if os.name != "nt":
            # Output is a dedicated per-run mount, never a project/source root.
            # The fixed non-root container UID must be able to publish results
            # even when the host orchestrator uses a different UID.
            request.output_root.resolve().chmod(0o777)
        unknown_environment = set(request.environment) - set(request.sandbox_spec.allowed_environment_variables)
        unsafe_environment = set(request.environment) - _SAFE_ENVIRONMENT
        if unknown_environment or unsafe_environment:
            names = ", ".join(sorted(unknown_environment | unsafe_environment))
            raise SandboxExecutorError(f"Execution environment variable is not allowlisted: {names}")
        limits = request.sandbox_spec.resource_limits
        memory = f"{limits.memory_mb}m"
        tmpfs_size = max(64 * 1024 * 1024, min(limits.memory_mb * 1024 * 1024 // 2, 2 * 1024**3))
        command = [
            self.docker,
            "run",
            "--rm",
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--user",
            "10001:10001",
            "--cpus",
            str(limits.cpu),
            "--memory",
            memory,
            "--memory-swap",
            memory,
            "--pids-limit",
            str(limits.maximum_processes),
            "--ulimit",
            f"fsize={limits.maximum_file_bytes}:{limits.maximum_file_bytes}",
            "--tmpfs",
            f"/execution:rw,exec,nosuid,nodev,size={tmpfs_size}",
            "--tmpfs",
            " /tmp:rw,noexec,nosuid,nodev,size=67108864".strip(),
            "--mount",
            f"type=bind,source={request.artifact_archive.resolve()},target=/input/environment.tar.gz,readonly",
            "--mount",
            f"type=bind,source={request.artifact_manifest.resolve()},target=/input/manifest.json,readonly",
            "--mount",
            f"type=bind,source={request.source_root.resolve()},target=/project,readonly",
            "--mount",
            f"type=bind,source={(request.tests_root or request.source_root).resolve()},target=/tests,readonly",
            "--mount",
            f"type=bind,source={request.output_root.resolve()},target=/output",
            "--mount",
            f"type=bind,source={spec_path.resolve()},target=/input/sandbox-spec.json,readonly",
            "--mount",
            f"type=bind,source={run_path.resolve()},target=/input/run-spec.json,readonly",
            "--workdir",
            "/project",
        ]
        if container_name:
            command.extend(["--name", container_name])
        for name, value in sorted(request.environment.items()):
            command.extend(["--env", f"{name}={value}"])
        command.extend(
            [
                request.image_digest,
                "run",
                "--sandbox-spec",
                "/input/sandbox-spec.json",
                "--run-spec",
                "/input/run-spec.json",
                "--artifact",
                "/input/environment.tar.gz",
                "--manifest",
                "/input/manifest.json",
                "--source-root",
                "/project",
                "--tests-root",
                "/tests",
                "--output-root",
                "/output",
                "--workspace-root",
                "/execution",
            ]
        )
        return command

    def execute(self, request: DockerExecutionRequest) -> SandboxResult:
        try:
            manifest = ArtifactManifest.from_dict(
                json.loads(request.artifact_manifest.resolve().read_text(encoding="utf-8"))
            )
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            raise SandboxExecutorError("Environment artifact manifest is invalid") from exc
        if manifest.image.image_digest != request.image_digest:
            raise SandboxExecutorError("Execution image digest does not match environment artifact")
        control = request.output_root.resolve() / ".sandbox-control"
        control.mkdir(parents=True, exist_ok=True)
        spec_path = control / "sandbox-spec.json"
        run_path = control / "run-spec.json"
        spec_path.write_text(json.dumps(request.sandbox_spec.as_dict(), sort_keys=True), encoding="utf-8")
        run_path.write_text(json.dumps(request.run_spec.as_dict(), sort_keys=True), encoding="utf-8")
        container_name = f"promptopt-sandbox-{uuid.uuid4().hex}"
        command = self.build_command(
            request,
            spec_path=spec_path,
            run_path=run_path,
            container_name=container_name,
        )
        try:
            completed = self.runner(
                command,
                text=True,
                capture_output=True,
                timeout=request.sandbox_spec.resource_limits.timeout_seconds + 30,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            self.runner(
                [self.docker, "rm", "--force", container_name],
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
            raise SandboxExecutorError("Docker execution exceeded its outer wall-clock deadline") from exc
        finally:
            spec_path.unlink(missing_ok=True)
            run_path.unlink(missing_ok=True)
            try:
                control.rmdir()
            except OSError:
                pass
        if completed.returncode != 0:
            stderr = (completed.stderr or "")[-request.sandbox_spec.resource_limits.maximum_output_bytes :]
            raise SandboxExecutorError(f"Sandbox container failed before returning a result: {stderr}")
        lines = [line for line in (completed.stdout or "").splitlines() if line.strip()]
        if not lines:
            raise SandboxExecutorError("Sandbox container returned no result")
        try:
            result = SandboxResult.from_dict(json.loads(lines[-1]))
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            raise SandboxExecutorError("Sandbox container returned an invalid result") from exc
        if (
            result.run_id != request.run_spec.run_id
            or result.environment_fingerprint != request.run_spec.environment_fingerprint
        ):
            raise SandboxExecutorError("Sandbox result identity does not match RunSpec")
        return result
