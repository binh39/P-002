from __future__ import annotations

import json
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from .package import add_distribution_metadata
from .workspace import docker_mount, temporary_workspace

SANDBOX_IMAGE = "testgen-sandbox:latest"


def _tail(text: str, limit: int = 4000) -> str:
    return text[-limit:].strip()


def _copy_source(source: Path, input_dir: Path) -> Path:
    destination = input_dir / source.name
    if source.is_dir():
        shutil.copytree(source, destination)
        add_distribution_metadata(source, input_dir)
    elif source.is_file():
        shutil.copy2(source, destination)
    else:
        raise FileNotFoundError(f"Source module does not exist: {source}")
    return destination


def _parse_sandbox_output(
    output_dir: Path,
    proc: subprocess.CompletedProcess[str],
    *,
    duration_seconds: float,
) -> dict[str, Any]:
    report_path = output_dir / "report.json"
    coverage_path = output_dir / "coverage.json"
    if not report_path.exists():
        error = _tail("\n".join(part for part in (proc.stdout, proc.stderr) if part))
        return {
            "build_ok": False,
            "build_error": error or f"pytest exited with status {proc.returncode}",
            "duration_seconds": duration_seconds,
        }

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        coverage = (
            json.loads(coverage_path.read_text(encoding="utf-8"))
            if coverage_path.exists()
            else {}
        )
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "build_ok": False,
            "build_error": f"Invalid sandbox report: {exc}",
            "duration_seconds": duration_seconds,
        }

    collection_errors = [
        collector.get("longrepr", "")
        for collector in report.get("collectors", [])
        if collector.get("outcome") == "failed"
    ]
    if proc.returncode not in (0, 1) or collection_errors:
        details = "\n".join(str(error) for error in collection_errors if error)
        error = _tail(details or proc.stdout or proc.stderr)
        return {
            "build_ok": False,
            "build_error": error or f"pytest exited with status {proc.returncode}",
            "report": report,
            "coverage": coverage,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "exit_code": proc.returncode,
            "duration_seconds": duration_seconds,
        }

    return {
        "build_ok": True,
        "build_error": "",
        "report": report,
        "coverage": coverage,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "exit_code": proc.returncode,
        "duration_seconds": duration_seconds,
    }


def run_in_sandbox(
    source_module_path: str | Path,
    test_code: str,
    timeout: int = 60,
    *,
    image: str = SANDBOX_IMAGE,
) -> dict[str, Any]:
    """Run untrusted generated tests in a networkless, resource-limited container."""
    source = Path(source_module_path).resolve()
    if timeout < 1:
        raise ValueError("timeout must be at least one second")

    run_id = uuid.uuid4().hex[:8]
    started = time.monotonic()
    with temporary_workspace(prefix=f"testgen_{run_id}_") as temp:
        workspace = Path(temp)
        input_dir = workspace / "input"
        output_dir = workspace / "output"
        input_dir.mkdir()
        output_dir.mkdir()
        copied_source = _copy_source(source, input_dir)
        test_file = input_dir / f"test_generated_{run_id}.py"
        test_file.write_text(test_code, encoding="utf-8")

        coverage_target = copied_source.stem if copied_source.is_file() else copied_source.name
        test_in_container = f"/app/input/{test_file.name}"
        command = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--memory",
            "512m",
            "--cpus",
            "1",
            "--pids-limit",
            "256",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=128m",
            *docker_mount(input_dir, "/app/input", read_only=True),
            *docker_mount(output_dir, "/app/output", read_only=False),
            "-e",
            "COVERAGE_FILE=/app/output/.coverage",
            "-w",
            "/app/input",
            image,
            "pytest",
            test_in_container,
            f"--cov={coverage_target}",
            "--cov-branch",
            "--cov-report=json:/app/output/coverage.json",
            "--json-report",
            "--json-report-file=/app/output/report.json",
            "-p",
            "no:cacheprovider",
            "-q",
        ]
        try:
            proc = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "build_ok": False,
                "build_error": f"timeout after {timeout}s",
                "stdout": exc.stdout or "",
                "stderr": exc.stderr or "",
                "duration_seconds": time.monotonic() - started,
            }
        except OSError as exc:
            return {
                "build_ok": False,
                "build_error": f"Unable to start Docker sandbox: {exc}",
                "duration_seconds": time.monotonic() - started,
            }

        return _parse_sandbox_output(
            output_dir,
            proc,
            duration_seconds=time.monotonic() - started,
        )
