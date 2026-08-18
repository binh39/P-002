import io
import json
import os
import sys
import tarfile
import zipfile
from pathlib import Path

from cloud.runtime_workspace import (
    RUNTIME_PROTOCOL_VERSION,
    RUNTIME_TOOL_PACKAGES,
    RuntimeProjectSpec,
    create_runtime_bundle,
    prepare_environment,
    prepare_runtime,
    safe_extract_runtime_bundle,
    safe_extract_zip,
)


def write_zip(path: Path, files: dict[str, str]) -> None:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    path.write_bytes(stream.getvalue())


def test_safe_extract_rejects_path_traversal(tmp_path):
    archive = tmp_path / "unsafe.zip"
    write_zip(archive, {"../outside.py": "pass"})

    try:
        safe_extract_zip(archive, tmp_path / "output")
    except ValueError as error:
        assert "Unsafe ZIP path" in str(error)
    else:
        raise AssertionError("path traversal must be rejected")


def test_runtime_bundle_contains_every_pytest_plugin_used_by_gepa():
    assert RUNTIME_PROTOCOL_VERSION == 3
    assert "pytest-repeat==0.9.4" in RUNTIME_TOOL_PACKAGES


def test_prepare_runtime_collects_tests_and_baseline_coverage(tmp_path):
    archive = tmp_path / "project.zip"
    write_zip(
        archive,
        {
            "demo/pkg/__init__.py": "def add(a, b):\n    return a + b\n",
            "demo/tests/test_pkg.py": "from pkg import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
        },
    )

    result, python = prepare_runtime(
        archive,
        tmp_path / "runtime",
        configured_source="pkg",
        configured_tests="tests",
        timeout_seconds=120,
    )

    assert result.status == "runtime_ready", result.error
    assert python is not None
    assert result.collected_tests == 1
    assert result.statement_coverage == 1.0
    assert result.branch_coverage == 1.0


def test_prepare_runtime_accepts_project_without_existing_tests(tmp_path):
    archive = tmp_path / "project-without-tests.zip"
    write_zip(
        archive,
        {"demo/pkg/__init__.py": "def add(a, b):\n    return a + b\n"},
    )

    result, python = prepare_runtime(
        archive,
        tmp_path / "runtime-without-tests",
        configured_source="pkg",
        configured_tests="tests",
        timeout_seconds=120,
    )

    assert result.status == "runtime_ready", result.error
    assert python is not None
    assert result.collected_tests == 0
    assert result.statement_coverage == 0.0


def test_prepare_environment_builds_one_reusable_bundle_for_multiple_projects(tmp_path):
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    write_zip(
        first,
        {
            "first/alpha/__init__.py": "def one():\n    return 1\n",
            "first/tests/test_alpha.py": "from alpha import one\n\ndef test_one():\n    assert one() == 1\n",
        },
    )
    write_zip(
        second,
        {
            "second/beta/__init__.py": "def two():\n    return 2\n",
            "second/tests/test_beta.py": "from beta import two\n\ndef test_two():\n    assert two() == 2\n",
        },
    )

    result, python = prepare_environment(
        [
            RuntimeProjectSpec("first", first, "alpha", "tests"),
            RuntimeProjectSpec("second", second, "beta", "tests"),
        ],
        tmp_path / "shared",
        timeout_seconds=120,
    )

    assert result.status == "runtime_ready", result.error
    assert python is not None
    assert set(result.projects) == {"first", "second"}
    assert all(item.collected_tests == 1 for item in result.projects.values())
    bundle = tmp_path / "runtime.tar.gz"
    create_runtime_bundle(python.parent.parent, bundle)
    restored_python = safe_extract_runtime_bundle(bundle, tmp_path / "restored")
    assert restored_python.is_file()


def test_prepare_environment_reports_atomic_dependency_conflict(tmp_path, monkeypatch):
    archive = tmp_path / "project.zip"
    write_zip(
        archive,
        {
            "demo/pkg/__init__.py": "VALUE = 1\n",
            "demo/tests/test_pkg.py": "from pkg import VALUE\n\ndef test_value():\n    assert VALUE == 1\n",
            "demo/requirements.txt": "shared-dependency==1\n",
        },
    )

    from cloud import runtime_workspace

    original_run = runtime_workspace._run

    def fail_resolution(result, name, command, cwd, deadline, output_limit):
        if name == "resolve shared dependencies":
            raise RuntimeError(
                "Dependency conflict prevented this project from joining the environment: "
                "shared-dependency has incompatible constraints"
            )
        return original_run(result, name, command, cwd, deadline, output_limit)

    monkeypatch.setattr(runtime_workspace, "_run", fail_resolution)
    result, python = prepare_environment(
        [RuntimeProjectSpec("candidate", archive, "pkg", "tests")],
        tmp_path / "conflict",
        timeout_seconds=120,
    )

    assert python is None
    assert result.status == "runtime_failed"
    assert "incompatible constraints" in (result.error or "")


def test_uploaded_gepa_run_restores_bundle_without_reinstalling_dependencies(tmp_path, monkeypatch):
    from cloud import run_job

    project_archive = tmp_path / "uploaded.zip"
    write_zip(
        project_archive,
        {
            "repo/src/actual_package/__init__.py": "VALUE = 1\n",
            "repo/tests/test_value.py": "from actual_package import VALUE\n",
        },
    )
    runtime_tree = tmp_path / "runtime-tree" / ".venv"
    executable = runtime_tree / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"prepared interpreter")
    bundle = tmp_path / "runtime.tar.gz"
    with tarfile.open(bundle, "w:gz") as archive:
        archive.add(runtime_tree, arcname=".venv")
    manifest = {
        "runtime_bundle_object": "inputs/runtime.tar.gz",
        "projects": [
            {
                "project": "friendly-name",
                "archive_object": "inputs/project.zip",
                "source_directory": "src",
                "test_directory": "tests",
            }
        ],
    }
    objects = {
        "inputs/dataset.jsonl": b'{"project":"friendly-name"}\n',
        "inputs/prompt.json": b"{}",
        "inputs/projects.json": json.dumps(manifest).encode(),
        "inputs/runtime.tar.gz": bundle.read_bytes(),
        "inputs/project.zip": project_archive.read_bytes(),
    }
    captured = {}

    def download(bucket, object_name, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(objects[object_name])

    def run(command):
        captured["command"] = command
        captured["test_python"] = os.environ.get("TESTGEN_PYTHON")
        layouts_path = Path(command[command.index("--project-layouts-file") + 1])
        captured["layouts"] = json.loads(layouts_path.read_text(encoding="utf-8"))
        artifacts = Path(command[command.index("--artifacts-dir") + 1])
        for relative in (
            "optimized_program.json",
            "prompts/gepa_proposed.json",
            "prompts/gepa_optimized.json",
            "final_validation.json",
        ):
            path = artifacts / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}", encoding="utf-8")
        return 0

    monkeypatch.setattr(run_job, "_download_object", download)
    monkeypatch.setattr(run_job, "_upload_dir", lambda *args: None)
    monkeypatch.setattr(run_job, "_run_cli", lambda command: (run(command), None))
    monkeypatch.setenv("TESTGEN_PYTHON", "before")
    monkeypatch.setenv("PROMPTOPT_RUNTIME_ROOT", str(tmp_path / "restored-runtime"))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_job",
            "--bucket",
            "bucket",
            "--artifacts-name",
            "runner-jobs/gepa/run/artifacts",
            "--dataset-object",
            "inputs/dataset.jsonl",
            "--prompt-object",
            "inputs/prompt.json",
            "--project-manifest-object",
            "inputs/projects.json",
        ],
    )

    assert run_job.main() == 0
    layout = captured["layouts"]["friendly-name"]
    assert layout["package_dir"].replace("\\", "/").endswith("/friendly-name/src")
    assert layout["import_root"] == layout["package_dir"]
    assert captured["test_python"] != "before"
    assert "prepare_runtime" not in " ".join(captured["command"])
