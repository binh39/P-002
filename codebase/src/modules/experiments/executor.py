import asyncio
import io
import os
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from src.core.errors import AppError

from .prompts import PromptBundle


@dataclass(frozen=True, slots=True)
class BaselineExecution:
    coverage_score: float | None


class DockerCoverUpExecutor:
    """Runs CoverUp outside the API process in a least-privilege Docker container."""

    def __init__(self, image: str, timeout_seconds: int, memory_mb: int, cpu: int):
        self.image, self.timeout_seconds, self.memory_mb, self.cpu = image, timeout_seconds, memory_mb, cpu

    async def execute(
        self, archive: bytes, source_directory: str, symbols: list[str], prompt: PromptBundle
    ) -> BaselineExecution:
        return await asyncio.to_thread(self._execute_sync, archive, source_directory, symbols, prompt)

    def _execute_sync(
        self, archive: bytes, source_directory: str, symbols: list[str], prompt: PromptBundle
    ) -> BaselineExecution:
        prompt.validate()
        with tempfile.TemporaryDirectory(prefix="promptopt-baseline-") as temp:
            root = Path(temp)
            project = root / "project"
            tests = root / "generated-tests"
            prompt_dir = root / "prompt"
            project.mkdir()
            tests.mkdir()
            prompt_dir.mkdir()
            (prompt_dir / "prompt.json").write_text(prompt.as_json(), encoding="utf-8")
            self._extract_archive(archive, project)
            source = (project / source_directory).resolve()
            if project not in source.parents or not source.is_dir():
                raise AppError(
                    422, "INVALID_SOURCE_DIRECTORY", "Configured source directory is absent from the archive"
                )
            command = [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--pids-limit",
                "256",
                "--memory",
                f"{self.memory_mb}m",
                "--cpus",
                str(self.cpu),
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,size=128m",
                "--mount",
                f"type=bind,src={project},dst=/workspace/project,readonly",
                "--mount",
                f"type=bind,src={tests},dst=/workspace/tests",
                "--mount",
                f"type=bind,src={prompt_dir},dst=/workspace/prompt,readonly",
            ]
            credentials = self._application_default_credentials()
            if credentials:
                command.extend(
                    [
                        "--mount",
                        f"type=bind,src={credentials},dst=/var/run/google-credentials.json,readonly",
                        "--env",
                        "GOOGLE_APPLICATION_CREDENTIALS=/var/run/google-credentials.json",
                    ]
                )
            for name in ("COVERUP_MODEL", "VERTEXAI_PROJECT", "VERTEXAI_LOCATION", "GOOGLE_API_KEY"):
                if value := os.getenv(name):
                    command.extend(["--env", f"{name}={value}"])
            command.extend(
                [
                    self.image,
                    "python",
                    "-m",
                    "coverup",
                    "--package-dir",
                    f"/workspace/project/{source_directory}",
                    "--tests",
                    "/workspace/tests",
                    "--target-symbol",
                    ",".join(symbols),
                    "--prompt",
                    "gpt-v2",
                    "--prompt-template-file",
                    "/workspace/prompt/prompt.json",
                    "--max-attempts",
                    "3",
                    "--repeat-tests",
                    "2",
                    "--max-concurrency",
                    "1",
                    "--no-checkpoint",
                ]
            )
            try:
                completed = subprocess.run(
                    command,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=self.timeout_seconds,
                    check=False,
                )
            except FileNotFoundError as exc:
                raise RuntimeError("Docker is not installed or not available to the baseline worker") from exc
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError("Baseline runner timed out") from exc
            if completed.returncode:
                raise RuntimeError(completed.stdout[-4000:] or "CoverUp baseline failed")
            return BaselineExecution(coverage_score=self._coverage_from_output(completed.stdout))

    @staticmethod
    def _coverage_from_output(output: str) -> float | None:
        for token in output.split():
            if token.endswith("%"):
                try:
                    return float(token[:-1]) / 100
                except ValueError:
                    continue
        return None

    @staticmethod
    def _application_default_credentials() -> Path | None:
        configured = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if configured and Path(configured).is_file():
            return Path(configured).resolve()
        app_data = os.getenv("APPDATA")
        candidate = Path(app_data) / "gcloud" / "application_default_credentials.json" if app_data else None
        return candidate.resolve() if candidate and candidate.is_file() else None

    @staticmethod
    def _extract_archive(archive: bytes, destination: Path) -> None:
        try:
            bundle = zipfile.ZipFile(io.BytesIO(archive))
        except zipfile.BadZipFile as exc:
            raise AppError(422, "INVALID_ZIP", "The project archive is not a valid ZIP") from exc
        for info in bundle.infolist():
            path = PurePosixPath(info.filename.replace("\\", "/"))
            if info.is_dir():
                continue
            if path.is_absolute() or ".." in path.parts:
                raise AppError(422, "INVALID_ZIP", "The archive contains an unsafe path")
            target = (destination / path.as_posix()).resolve()
            if destination not in target.parents:
                raise AppError(422, "INVALID_ZIP", "The archive contains an unsafe path")
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(info) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
