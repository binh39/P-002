import asyncio
import io
import json
import os
import shutil
import stat
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
    statement_coverage: float | None
    branch_coverage: float | None
    artifacts: dict[str, bytes]


class DockerCoverUpExecutor:
    """Runs CoverUp outside the API process in a least-privilege Docker container."""

    def __init__(
        self,
        image: str,
        timeout_seconds: int,
        memory_mb: int,
        cpu: int,
        max_files: int,
        max_uncompressed_bytes: int,
    ):
        self.image, self.timeout_seconds, self.memory_mb, self.cpu = image, timeout_seconds, memory_mb, cpu
        self.max_files = max_files
        self.max_uncompressed_bytes = max_uncompressed_bytes

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
            artifacts_dir = root / "artifacts"
            project.mkdir()
            tests.mkdir()
            prompt_dir.mkdir()
            artifacts_dir.mkdir()
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
                "--mount",
                f"type=bind,src={artifacts_dir},dst=/workspace/artifacts",
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
                    "--trace-file",
                    "/workspace/artifacts/attempt_trace.jsonl",
                    "--log-file",
                    "/workspace/artifacts/coverup.log",
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
            (artifacts_dir / "coverup.stdout.log").write_text(completed.stdout, encoding="utf-8")
            (artifacts_dir / "prompt.json").write_text(prompt.as_json(), encoding="utf-8")
            shutil.make_archive(str(artifacts_dir / "generated_tests"), "zip", tests)
            report = self._run_coverage(project, tests, artifacts_dir, source_directory)
            totals = report.get("totals", {})
            statement = self._ratio(totals.get("covered_lines"), totals.get("num_statements"))
            branch = self._ratio(totals.get("covered_branches"), totals.get("num_branches"))
            score = None if statement is None else statement if branch is None else 0.4 * statement + 0.6 * branch
            artifacts = {path.name: path.read_bytes() for path in artifacts_dir.iterdir() if path.is_file()}
            return BaselineExecution(score, statement, branch, artifacts)

    def _run_coverage(self, project: Path, tests: Path, artifacts: Path, source_directory: str) -> dict:
        docker = [
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
            f"type=bind,src={tests},dst=/workspace/tests,readonly",
            "--mount",
            f"type=bind,src={artifacts},dst=/workspace/artifacts",
            "--env",
            "COVERAGE_FILE=/workspace/artifacts/coverage.data",
            self.image,
        ]
        run_command = [
            *docker,
            "coverage",
            "run",
            "--branch",
            f"--source=/workspace/project/{source_directory}",
            "-m",
            "pytest",
            "-q",
            "/workspace/tests",
        ]
        completed = subprocess.run(
            run_command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=self.timeout_seconds,
            check=False,
        )
        (artifacts / "coverage.stdout.log").write_text(completed.stdout, encoding="utf-8")
        if completed.returncode:
            raise RuntimeError(completed.stdout[-4000:] or "Generated tests failed coverage validation")
        json_command = [
            *docker,
            "coverage",
            "json",
            "-o",
            "/workspace/artifacts/coverage_after.json",
        ]
        exported = subprocess.run(
            json_command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=self.timeout_seconds,
            check=False,
        )
        if exported.returncode:
            raise RuntimeError(exported.stdout[-4000:] or "Coverage JSON export failed")
        return json.loads((artifacts / "coverage_after.json").read_text(encoding="utf-8"))

    @staticmethod
    def _ratio(covered, total) -> float | None:
        if total is None or int(total) == 0:
            return None
        return int(covered or 0) / int(total)

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

    def _extract_archive(self, archive: bytes, destination: Path) -> None:
        try:
            bundle = zipfile.ZipFile(io.BytesIO(archive))
        except zipfile.BadZipFile as exc:
            raise AppError(422, "INVALID_ZIP", "The project archive is not a valid ZIP") from exc
        entries = [info for info in bundle.infolist() if not info.is_dir()]
        if len(entries) > self.max_files:
            raise AppError(413, "TOO_MANY_ARCHIVE_FILES", "The archive contains too many files")
        if sum(info.file_size for info in entries) > self.max_uncompressed_bytes:
            raise AppError(413, "RUNNER_ARCHIVE_TOO_LARGE", "The archive exceeds the runner extraction limit")
        for info in entries:
            path = PurePosixPath(info.filename.replace("\\", "/"))
            mode = info.external_attr >> 16
            if mode and stat.S_IFMT(mode) not in {0, stat.S_IFREG}:
                raise AppError(422, "INVALID_ZIP_ENTRY", "The archive contains a non-regular file")
            if path.is_absolute() or ".." in path.parts:
                raise AppError(422, "INVALID_ZIP", "The archive contains an unsafe path")
            target = (destination / path.as_posix()).resolve()
            if destination not in target.parents:
                raise AppError(422, "INVALID_ZIP", "The archive contains an unsafe path")
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(info) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
