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
from .schemas import ExperimentSettings
from .traces import as_jsonl, parse_coverup_log


@dataclass(frozen=True, slots=True)
class BaselineExecution:
    coverage_score: float | None
    statement_coverage: float | None
    branch_coverage: float | None
    artifacts: dict[str, bytes]
    target_metrics: dict[str, dict[str, float | int | None]]


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
        network_mode: str = "none",
    ):
        self.image, self.timeout_seconds, self.memory_mb, self.cpu = image, timeout_seconds, memory_mb, cpu
        self.max_files = max_files
        self.max_uncompressed_bytes = max_uncompressed_bytes
        self.network_mode = network_mode

    async def execute(
        self,
        archive: bytes,
        source_directory: str,
        symbols: list[str],
        prompt: PromptBundle,
        settings: ExperimentSettings | None = None,
    ) -> BaselineExecution:
        return await asyncio.to_thread(
            self._execute_sync, archive, source_directory, symbols, prompt, settings or ExperimentSettings()
        )

    def _execute_sync(
        self,
        archive: bytes,
        source_directory: str,
        symbols: list[str],
        prompt: PromptBundle,
        settings: ExperimentSettings,
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
                self.network_mode,
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
            for name in ("VERTEXAI_PROJECT", "VERTEXAI_LOCATION", "GOOGLE_API_KEY"):
                if value := os.getenv(name):
                    command.extend(["--env", f"{name}={value}"])
            command.extend(["--env", f"COVERUP_MODEL={settings.coverup_model}"])
            command.extend(["--env", "PROMPTOPT_PROJECT_ROOT=/workspace/project"])
            command.extend(["--env", f"PROMPTOPT_PACKAGE_DIR=/workspace/project/{source_directory}"])
            command.extend(["--env", "PROMPTOPT_SETUP_SITE=/workspace/tests/.promptopt-site"])
            command.extend(["--env", "PROMPTOPT_SETUP_REPORT=/workspace/artifacts/project_setup.json"])
            command.extend(["--env", "PROMPTOPT_PROMPT_FILE=/workspace/prompt/prompt.json"])
            command.extend(["--env", f"PROMPTOPT_TARGET_SYMBOLS={json.dumps(symbols)}"])
            command.extend(
                [
                    self.image,
                    "python",
                    "/opt/promptopt/runner_entry.py",
                    "--package-dir",
                    f"/workspace/project/{source_directory}",
                    "--tests-dir",
                    "/workspace/tests",
                    "--prompt",
                    "gpt-v2",
                    "--log-file",
                    "/workspace/artifacts/coverup.log",
                    "--model",
                    settings.coverup_model,
                    "--max-attempts",
                    str(settings.max_attempts),
                    "--repeat-tests",
                    str(settings.repeat_tests),
                    "--max-concurrency",
                    str(settings.max_concurrency),
                    "--no-checkpoint",
                ]
            )
            if settings.rate_limit:
                command.extend(["--rate-limit", str(settings.rate_limit)])
            if settings.pytest_args:
                command.extend(["--pytest-args", settings.pytest_args])
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
            coverup_log = artifacts_dir / "coverup.log"
            if coverup_log.is_file():
                (artifacts_dir / "attempt_trace.jsonl").write_bytes(
                    as_jsonl(parse_coverup_log(coverup_log.read_text(encoding="utf-8")))
                )
            shutil.make_archive(str(artifacts_dir / "generated_tests"), "zip", tests)
            report = self._run_coverage(project, tests, artifacts_dir, source_directory)
            target_metrics = self._target_metrics(report, symbols)
            (artifacts_dir / "target_coverage.json").write_text(
                json.dumps(target_metrics, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            statement, branch, score = self._aggregate_target_metrics(target_metrics)
            artifacts = {path.name: path.read_bytes() for path in artifacts_dir.iterdir() if path.is_file()}
            return BaselineExecution(score, statement, branch, artifacts, target_metrics)

    @classmethod
    def _target_metrics(cls, report: dict, symbols: list[str]) -> dict[str, dict[str, float | int | None]]:
        functions = [
            (name, data)
            for file_data in report.get("files", {}).values()
            for name, data in file_data.get("functions", {}).items()
            if name
        ]
        result = {}
        for symbol in symbols:
            matches = [data for name, data in functions if name == symbol or name.endswith(f".{symbol}")]
            if len(matches) != 1:
                result[symbol] = {
                    "valid": False,
                    "covered_statements": 0,
                    "num_statements": 0,
                    "covered_branches": 0,
                    "num_branches": 0,
                    "statement_coverage": None,
                    "branch_coverage": None,
                    "score": 0.0,
                }
                continue
            summary = matches[0]["summary"]
            covered_statements = int(summary.get("covered_lines", 0))
            num_statements = int(summary.get("num_statements", 0))
            covered_branches = int(summary.get("covered_branches", 0))
            if covered_statements == 0:
                covered_branches = 0
            num_branches = int(summary.get("num_branches", 0))
            statement = cls._ratio(covered_statements, num_statements)
            branch = cls._ratio(covered_branches, num_branches)
            score = statement if branch is None else 0.4 * (statement or 0.0) + 0.6 * branch
            result[symbol] = {
                "valid": True,
                "covered_statements": covered_statements,
                "num_statements": num_statements,
                "covered_branches": covered_branches,
                "num_branches": num_branches,
                "statement_coverage": statement,
                "branch_coverage": branch,
                "score": score,
            }
        return result

    @staticmethod
    def _aggregate_target_metrics(metrics: dict[str, dict]) -> tuple[float | None, float | None, float | None]:
        valid = [value for value in metrics.values() if value.get("valid")]
        if not valid:
            return None, None, 0.0
        covered_statements = sum(value["covered_statements"] for value in valid)
        num_statements = sum(value["num_statements"] for value in valid)
        covered_branches = sum(value["covered_branches"] for value in valid)
        num_branches = sum(value["num_branches"] for value in valid)
        statement = covered_statements / num_statements if num_statements else None
        branch = covered_branches / num_branches if num_branches else None
        score = statement if branch is None else 0.4 * (statement or 0.0) + 0.6 * branch
        return statement, branch, score

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
            "--env",
            "PYTHONPATH=/workspace/tests/.promptopt-site:/workspace/project",
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
        if completed.returncode not in {0, 5}:
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
