import hashlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from google.cloud import storage
from project_setup import prepare_project
from traces import as_jsonl, parse_coverup_log


def main() -> int:
    bucket_name = os.environ["PROMPTOPT_JOB_BUCKET"]
    prefix = os.environ["PROMPTOPT_JOB_PREFIX"].strip("/")
    bucket = storage.Client().bucket(bucket_name)
    with tempfile.TemporaryDirectory(prefix="promptopt-cloud-run-job-") as temporary:
        root = Path(temporary)
        project = root / "project"
        tests = root / "generated-tests"
        artifacts = root / "artifacts"
        project.mkdir()
        tests.mkdir()
        artifacts.mkdir()
        result = {"status": "failed", "error": "Runner did not finish"}
        try:
            source_archive = root / "source.zip"
            prompt_file = root / "prompt.json"
            _download(bucket, f"{prefix}/source.zip", source_archive)
            _download(bucket, f"{prefix}/prompt.json", prompt_file)
            spec = json.loads(bucket.blob(f"{prefix}/spec.json").download_as_text())
            prompt = json.loads(prompt_file.read_text(encoding="utf-8"))
            if _prompt_digest(prompt) != spec["prompt_digest"]:
                raise RuntimeError("Prompt digest does not match the immutable job spec")
            _extract_archive(
                source_archive.read_bytes(),
                project,
                int(os.getenv("PROMPTOPT_MAX_FILES", "10000")),
                int(os.getenv("PROMPTOPT_MAX_UNCOMPRESSED_BYTES", str(100 * 1024 * 1024))),
            )
            source_directory = spec["source_directory"]
            settings = spec.get("settings", {})
            source = (project / source_directory).resolve()
            if project not in source.parents or not source.is_dir():
                raise RuntimeError("Configured source directory is absent from the archive")

            setup_report, environment = prepare_project(project, source, os.environ.copy())
            (artifacts / "project_setup.json").write_text(
                json.dumps(setup_report.as_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            environment["PROMPTOPT_PROMPT_FILE"] = str(prompt_file)
            environment["PROMPTOPT_TARGET_SYMBOLS"] = json.dumps(spec["symbols"])
            coverup = _run(
                [
                    sys.executable,
                    "/opt/promptopt/runner_entry.py",
                    "--package-dir",
                    str(source),
                    "--tests-dir",
                    str(tests),
                    "--prompt",
                    "gpt-v2",
                    "--log-file",
                    str(artifacts / "coverup.log"),
                    "--model",
                    os.environ["COVERUP_MODEL"],
                    "--max-attempts",
                    str(settings.get("max_attempts", 3)),
                    "--repeat-tests",
                    str(settings.get("repeat_tests", 2)),
                    "--max-concurrency",
                    str(settings.get("max_concurrency", 10)),
                    "--no-checkpoint",
                    *(["--rate-limit", str(settings["rate_limit"])] if settings.get("rate_limit") else []),
                    *(["--pytest-args", settings["pytest_args"]] if settings.get("pytest_args") else []),
                ],
                environment,
                int(os.getenv("PROMPTOPT_RUNNER_TIMEOUT_SECONDS", "900")),
            )
            (artifacts / "coverup.stdout.log").write_text(coverup.stdout, encoding="utf-8")
            if coverup.returncode:
                raise RuntimeError(coverup.stdout[-4000:] or "CoverUp execution failed")
            shutil.copyfile(prompt_file, artifacts / "prompt.json")
            coverup_log = artifacts / "coverup.log"
            if coverup_log.is_file():
                (artifacts / "attempt_trace.jsonl").write_bytes(
                    as_jsonl(parse_coverup_log(coverup_log.read_text(encoding="utf-8")))
                )
            shutil.make_archive(str(artifacts / "generated_tests"), "zip", tests)
            report = _coverage(project, tests, artifacts, source_directory, environment)
            target_metrics = _target_metrics(report, spec["symbols"])
            (artifacts / "target_coverage.json").write_text(
                json.dumps(target_metrics, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            statement, branch, score = _aggregate(target_metrics)
            result = {
                "status": "succeeded",
                "coverage_score": score,
                "statement_coverage": statement,
                "branch_coverage": branch,
                "target_metrics": target_metrics,
                "artifacts": sorted(path.name for path in artifacts.iterdir() if path.is_file()),
            }
        except Exception as exc:
            result = {"status": "failed", "error": str(exc)[-4000:]}
        for path in artifacts.iterdir():
            if path.is_file():
                bucket.blob(f"{prefix}/artifacts/{path.name}").upload_from_filename(path)
        bucket.blob(f"{prefix}/result.json").upload_from_string(
            json.dumps(result, ensure_ascii=False), content_type="application/json"
        )
        return 0 if result["status"] == "succeeded" else 1


def _download(bucket, object_name: str, destination: Path) -> None:
    bucket.blob(object_name).download_to_filename(destination)


def _prompt_digest(prompt: dict) -> str:
    return hashlib.sha256(json.dumps(prompt, sort_keys=True).encode()).hexdigest()[:16]


def _run(command: list[str], environment: dict[str, str], timeout: int):
    try:
        return subprocess.run(
            command,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Runner command timed out") from exc


def _coverage(project: Path, tests: Path, artifacts: Path, source_directory: str, environment: dict) -> dict:
    coverage_environment = {**environment, "COVERAGE_FILE": str(artifacts / "coverage.data")}
    python_path = str(project)
    if coverage_environment.get("PYTHONPATH"):
        python_path += os.pathsep + coverage_environment["PYTHONPATH"]
    coverage_environment["PYTHONPATH"] = python_path
    timeout = int(os.getenv("PROMPTOPT_RUNNER_TIMEOUT_SECONDS", "900"))
    completed = _run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "--branch",
            f"--source={project / source_directory}",
            "-m",
            "pytest",
            "-q",
            str(tests),
        ],
        coverage_environment,
        timeout,
    )
    (artifacts / "coverage.stdout.log").write_text(completed.stdout, encoding="utf-8")
    if completed.returncode not in {0, 5}:
        raise RuntimeError(completed.stdout[-4000:] or "Generated tests failed coverage validation")
    exported = _run(
        [
            sys.executable,
            "-m",
            "coverage",
            "json",
            "-o",
            str(artifacts / "coverage_after.json"),
        ],
        coverage_environment,
        timeout,
    )
    if exported.returncode:
        raise RuntimeError(exported.stdout[-4000:] or "Coverage JSON export failed")
    return json.loads((artifacts / "coverage_after.json").read_text(encoding="utf-8"))


def _target_metrics(report: dict, symbols: list[str]) -> dict[str, dict]:
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
        statement = covered_statements / num_statements if num_statements else None
        branch = covered_branches / num_branches if num_branches else None
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


def _aggregate(metrics: dict[str, dict]) -> tuple[float | None, float | None, float]:
    valid = [metric for metric in metrics.values() if metric.get("valid")]
    if not valid:
        return None, None, 0.0
    covered_statements = sum(metric["covered_statements"] for metric in valid)
    num_statements = sum(metric["num_statements"] for metric in valid)
    covered_branches = sum(metric["covered_branches"] for metric in valid)
    num_branches = sum(metric["num_branches"] for metric in valid)
    statement = covered_statements / num_statements if num_statements else None
    branch = covered_branches / num_branches if num_branches else None
    score = statement if branch is None else 0.4 * (statement or 0.0) + 0.6 * branch
    return statement, branch, score or 0.0


def _extract_archive(content: bytes, destination: Path, max_files: int, max_bytes: int) -> None:
    try:
        bundle = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as exc:
        raise RuntimeError("Project archive is not a valid ZIP") from exc
    entries = [entry for entry in bundle.infolist() if not entry.is_dir()]
    if len(entries) > max_files:
        raise RuntimeError("Project archive contains too many files")
    if sum(entry.file_size for entry in entries) > max_bytes:
        raise RuntimeError("Project archive exceeds the extraction limit")
    for entry in entries:
        path = PurePosixPath(entry.filename.replace("\\", "/"))
        mode = entry.external_attr >> 16
        if mode and stat.S_IFMT(mode) not in {0, stat.S_IFREG}:
            raise RuntimeError("Project archive contains a non-regular file")
        if path.is_absolute() or ".." in path.parts:
            raise RuntimeError("Project archive contains an unsafe path")
        target = (destination / path.as_posix()).resolve()
        if destination not in target.parents:
            raise RuntimeError("Project archive contains an unsafe path")
        target.parent.mkdir(parents=True, exist_ok=True)
        with bundle.open(entry) as source, target.open("wb") as output:
            shutil.copyfileobj(source, output)


if __name__ == "__main__":
    raise SystemExit(main())
