import io
import json
import os
import stat
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

from cloud.runtime_workspace import (
    RUNTIME_PROTOCOL_VERSION,
    RUNTIME_TOOL_PACKAGES,
    RuntimeProjectSpec,
    _legacy_metadata_requirements,
    _redact_text,
    _test_requirement_files,
    _validate_extra_package_index,
    _validate_project_id,
    _validate_project_python,
    detect_layout,
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


def test_runtime_diagnostics_redact_private_index_credentials():
    value = _redact_text("https://user:secret@example.test/simple/pkg")
    assert "secret" not in value
    assert value == "https://example.test/simple/pkg"


def test_runtime_preparer_rejects_credential_bearing_index_even_from_manifest():
    for value in (
        "https://user:secret@example.test/simple",
        "https://example.test/simple?token=secret",
        "https://example.test/simple?deploy_password=secret",
    ):
        try:
            _validate_extra_package_index(value)
        except ValueError as error:
            assert "must not contain credentials" in str(error)
        else:
            raise AssertionError("credential-bearing package index must be rejected")


def test_runtime_bundle_restore_supports_legacy_tarfile_api(tmp_path, monkeypatch):
    bundle = tmp_path / "runtime.tar.gz"
    with tarfile.open(bundle, "w:gz") as archive:
        payload = b"prepared-python"
        executable = "Scripts/python.exe" if os.name == "nt" else "bin/python"
        info = tarfile.TarInfo(f".venv/{executable}")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))

    original_extractall = tarfile.TarFile.extractall

    def legacy_extractall(self, path=".", *args, **kwargs):
        if "filter" in kwargs:
            raise TypeError("legacy TarFile.extractall has no filter argument")
        return original_extractall(self, path, *args, **kwargs)

    monkeypatch.setattr(tarfile.TarFile, "extractall", legacy_extractall)
    python = safe_extract_runtime_bundle(bundle, tmp_path / "restored")

    assert python == tmp_path / "restored" / ".venv" / Path(executable)


def test_runtime_preparer_rejects_path_unsafe_project_id_before_extraction(tmp_path):
    archive = tmp_path / "project.zip"
    write_zip(archive, {"demo/pkg/__init__.py": "VALUE = 1\n"})

    result, python = prepare_environment(
        [RuntimeProjectSpec("../outside", archive, "pkg", "tests")],
        tmp_path / "workspace",
        timeout_seconds=30,
    )

    assert python is None
    assert result.status == "runtime_failed"
    assert "path-safe" in (result.error or "")
    with pytest.raises(ValueError, match="path-safe"):
        _validate_project_id("nested/project")


def test_safe_extract_ignores_symbolic_links(tmp_path):
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        link = zipfile.ZipInfo("project/link.py")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        bundle.writestr(link, "target.py")
        bundle.writestr("project/target.py", "def target():\n    return 1\n")

    output = tmp_path / "output"
    safe_extract_zip(archive, output)

    assert not (output / "project" / "link.py").exists()
    assert (output / "project" / "target.py").is_file()


def test_runtime_bundle_contains_every_pytest_plugin_used_by_gepa():
    assert RUNTIME_PROTOCOL_VERSION == 11
    assert "pytest-asyncio>=0.23,<2" in RUNTIME_TOOL_PACKAGES
    assert "pytest-repeat>=0.9,<1" in RUNTIME_TOOL_PACKAGES
    assert "pytest-timeout>=2.3,<3" in RUNTIME_TOOL_PACKAGES
    assert "coverage>=7,<8" in RUNTIME_TOOL_PACKAGES
    assert "slipcover==1.0.18" in RUNTIME_TOOL_PACKAGES


def test_legacy_setup_metadata_dependencies_are_discovered_without_execution(tmp_path):
    project = tmp_path / "legacy"
    project.mkdir()
    (project / "setup.py").write_text(
        "from setuptools import setup\n"
        "MARKER = '; python_version >= \"3.10\"'\n"
        "RUNTIME = ['psutil>=5', 'colorama; platform_system == \"Windows\"']\n"
        "TESTS = ['pytest-mock' + MARKER]\n"
        "KWARGS = {'name': 'legacy'}\n"
        "KWARGS['install_requires'] = RUNTIME\n"
        "KWARGS['tests_require'] = TESTS\n"
        "KWARGS['extras_require'] = {'test': ['freezegun'], 'docs': ['sphinx'], "
        "': python_version >= \"3.10\"': ['decorator']}\n"
        "setup(**KWARGS)\n",
        encoding="utf-8",
    )
    (project / "setup.cfg").write_text(
        "[options]\ninstall_requires =\n    requests>=2\n"
        "[options.extras_require]\ntesting =\n    freezegun\ndocs =\n    mkdocs\n",
        encoding="utf-8",
    )

    requirements = _legacy_metadata_requirements(project)

    assert requirements == [
        "requests>=2",
        "freezegun",
        "psutil>=5",
        'colorama; platform_system == "Windows"',
        'decorator; python_version >= "3.10"',
        'pytest-mock; python_version >= "3.10"',
    ]


def test_detect_layout_supports_lib_package_layout(tmp_path):
    project = tmp_path / "project"
    package = project / "lib" / "example"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")

    source, tests = detect_layout(project)

    assert source == package
    assert tests == project / "tests"


def test_detect_layout_does_not_select_root_test_package_as_source(tmp_path):
    project = tmp_path / "project"
    package = project / "tqdm"
    tests = project / "tests"
    package.mkdir(parents=True)
    tests.mkdir()
    (package / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tests / "__init__.py").write_text("", encoding="utf-8")
    (tests / "test_value.py").write_text("def test_value():\n    assert True\n", encoding="utf-8")

    # A previous runtime protocol could persist ``tests`` as the configured
    # source. Retrying must repair that stale value instead of trusting it.
    source, detected_tests = detect_layout(project, configured_source="tests")

    assert source == package
    assert detected_tests == tests


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


def test_runtime_admission_exports_project_venv_to_console_entrypoints(tmp_path, monkeypatch):
    archive = tmp_path / "console-entrypoint.zip"
    write_zip(
        archive,
        {
            "demo/pkg/__init__.py": "def value():\n    return 1\n",
            "demo/tests/test_console.py": (
                "import os\n"
                "import subprocess\n"
                "import sys\n\n"
                "def test_console_entrypoint():\n"
                "    completed = subprocess.run([\"promptopt-console\"], check=True, "
                "capture_output=True, text=True)\n"
                "    assert completed.stdout.strip() == \"runtime-ok\"\n"
                "    assert os.environ[\"TESTGEN_PYTHON\"] == sys.executable\n"
                "    assert os.environ[\"VIRTUAL_ENV\"]\n"
            ),
        },
    )
    runtime_dir = tmp_path / "runtime-with-console-entrypoint"
    from cloud import runtime_workspace

    original_run = runtime_workspace._run
    created = False

    def install_console_entrypoint(result, name, command, cwd, deadline, output_limit, **kwargs):
        nonlocal created
        if name != "create project runtime" and not created:
            bin_dir = runtime_dir / ".venv" / ("Scripts" if os.name == "nt" else "bin")
            bin_dir.mkdir(parents=True, exist_ok=True)
            if os.name == "nt":
                (bin_dir / "promptopt-console.cmd").write_text(
                    "@echo off\r\necho runtime-ok\r\n", encoding="utf-8"
                )
            else:
                script = bin_dir / "promptopt-console"
                script.write_text("#!/bin/sh\necho runtime-ok\n", encoding="utf-8")
                script.chmod(0o755)
            created = True
        return original_run(result, name, command, cwd, deadline, output_limit, **kwargs)

    monkeypatch.setattr(runtime_workspace, "_run", install_console_entrypoint)
    result, python = prepare_runtime(
        archive,
        runtime_dir,
        configured_source="pkg",
        configured_tests="tests",
        timeout_seconds=120,
    )

    assert result.status == "runtime_ready", result.error
    assert python is not None
    assert created


def test_prepare_runtime_accepts_project_without_existing_tests(tmp_path):
    archive = tmp_path / "project-without-tests.zip"
    write_zip(
        archive,
        {
            "demo/pkg/__init__.py": "def add(a, b):\n    return a + b\n",
            # This looks like a test to a project-root collection, but it is
            # an executable integration helper and must never be imported.
            "demo/test/integration/library/async_test.py": ("raise RuntimeError('project root was collected')\n"),
        },
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
    assert result.test_directory == ".promptopt-empty-tests"


def test_prepare_runtime_treats_upstream_collection_failure_as_diagnostic(tmp_path):
    archive = tmp_path / "project-with-broken-upstream-config.zip"
    write_zip(
        archive,
        {
            "demo/pkg/__init__.py": "def add(a, b):\n    return a + b\n",
            "demo/tests/test_pkg.py": "from pkg import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
            "demo/pytest.ini": "[pytest]\naddopts = --definitely-not-a-real-pytest-option\n",
        },
    )

    result, python = prepare_runtime(
        archive,
        tmp_path / "runtime-with-broken-upstream-config",
        configured_source="pkg",
        configured_tests="tests",
        timeout_seconds=120,
    )

    assert result.status == "runtime_ready", result.error
    assert python is not None
    collect = next(item for item in result.commands if item.name.startswith("collect tests"))
    assert collect.return_code not in (0, 5)
    assert any(item.name.startswith("zero baseline") for item in result.commands)
    assert result.statement_coverage == 0.0


def test_prepare_runtime_falls_back_when_baseline_produces_no_coverage_data(tmp_path, monkeypatch):
    from cloud import runtime_workspace

    archive = tmp_path / "project-with-empty-baseline-coverage.zip"
    write_zip(
        archive,
        {
            "demo/pkg/__init__.py": "def add(a, b):\n    return a + b\n",
            "demo/tests/test_pkg.py": "from pkg import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
        },
    )
    original_run = runtime_workspace._run
    rejected_report = False

    def empty_first_report(result, name, command, cwd, deadline, output_limit, **kwargs):
        nonlocal rejected_report
        if name.startswith("coverage report for") and not rejected_report:
            rejected_report = True
            completed = runtime_workspace.CommandResult(
                name=name,
                command=command,
                return_code=1,
                duration_seconds=0.01,
                output="No data to report.\n",
            )
            result.commands.append(completed)
            return completed
        return original_run(result, name, command, cwd, deadline, output_limit, **kwargs)

    monkeypatch.setattr(runtime_workspace, "_run", empty_first_report)

    result, python = prepare_runtime(
        archive,
        tmp_path / "runtime-with-empty-baseline-coverage",
        configured_source="pkg",
        configured_tests="tests",
        timeout_seconds=120,
    )

    assert result.status == "runtime_ready", result.error
    assert python is not None
    assert result.statement_coverage == 0.0
    assert rejected_report
    assert any(item.name.startswith("zero baseline after empty coverage") for item in result.commands)


def test_prepare_runtime_falls_back_when_upstream_collection_times_out(tmp_path):
    archive = tmp_path / "project-with-hanging-collection.zip"
    write_zip(
        archive,
        {
            "demo/pkg/__init__.py": "VALUE = 1\n",
            "demo/tests/test_hang.py": "import time\ntime.sleep(5)\n\ndef test_value():\n    assert True\n",
        },
    )

    result, python = prepare_runtime(
        archive,
        tmp_path / "runtime-with-hanging-collection",
        configured_source="pkg",
        configured_tests="tests",
        timeout_seconds=120,
        admission_command_timeout_seconds=1,
    )

    assert result.status == "runtime_ready", result.error
    assert python is not None
    collect = next(item for item in result.commands if item.name.startswith("collect tests"))
    assert collect.timed_out is True
    assert any(item.name.startswith("zero baseline") for item in result.commands)


def test_prepare_runtime_prefers_unit_tests_over_integration_harnesses(tmp_path):
    archive = tmp_path / "project-with-mixed-tests.zip"
    write_zip(
        archive,
        {
            "demo/pkg/__init__.py": "def add(a, b):\n    return a + b\n",
            "demo/test/units/test_pkg.py": ("from pkg import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"),
            "demo/test/integration/library/async_test.py": (
                "raise RuntimeError('integration harness was collected')\n"
            ),
        },
    )

    result, python = prepare_runtime(
        archive,
        tmp_path / "runtime-with-mixed-tests",
        configured_source="pkg",
        configured_tests="tests",
        timeout_seconds=120,
    )

    assert result.status == "runtime_ready", result.error
    assert python is not None
    assert result.collected_tests == 1
    assert result.test_directory == "test/units"


def test_test_requirements_follow_selected_suite_without_project_specific_mapping(tmp_path):
    root = tmp_path / "project"
    tests = root / "test" / "units"
    requirements = root / "test" / "tooling" / "requirements"
    tests.mkdir(parents=True)
    requirements.mkdir(parents=True)
    unit_requirements = requirements / "units.txt"
    integration_requirements = requirements / "integration.txt"
    unit_requirements.write_text("pytest-mock\n", encoding="utf-8")
    integration_requirements.write_text("docker\n", encoding="utf-8")

    assert _test_requirement_files(root, tests) == [unit_requirements.resolve()]


def test_project_python_requirement_is_validated_before_runtime_commands(tmp_path):
    archive = tmp_path / "incompatible-python.zip"
    write_zip(
        archive,
        {
            "demo/pyproject.toml": ('[project]\nname = "demo"\nversion = "1.0.0"\nrequires-python = ">=99"\n'),
            "demo/pkg/__init__.py": "VALUE = 1\n",
        },
    )

    result, python = prepare_runtime(
        archive,
        tmp_path / "incompatible-python-runtime",
        configured_source="pkg",
        timeout_seconds=120,
    )

    assert python is None
    assert result.status == "runtime_failed"
    assert "requires Python >=99" in (result.error or "")
    assert "selected runtime provides Python" in (result.error or "")
    assert result.commands == []


def test_invalid_project_python_requirement_is_reported_as_project_metadata_error(tmp_path):
    root = tmp_path / "invalid-metadata"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "1.0.0"\nrequires-python = "not a version"\n',
        encoding="utf-8",
    )

    try:
        _validate_project_python(root, "demo")
    except ValueError as error:
        assert "invalid requires-python specifier" in str(error)
    else:
        raise AssertionError("invalid project metadata must be rejected")


def test_prepare_runtime_accepts_failing_upstream_tests_when_coverage_is_measurable(tmp_path):
    archive = tmp_path / "project-with-failing-test.zip"
    write_zip(
        archive,
        {
            "demo/pkg/__init__.py": "def value():\n    return 1\n",
            "demo/tests/test_pkg.py": (
                "from pkg import value\n\ndef test_upstream_assumption():\n    assert value() == 2\n"
            ),
        },
    )

    result, python = prepare_runtime(
        archive,
        tmp_path / "runtime-with-failing-test",
        configured_source="pkg",
        configured_tests="tests",
        timeout_seconds=120,
    )

    assert result.status == "runtime_ready", result.error
    assert python is not None
    assert result.collected_tests == 1
    baseline = next(item for item in result.commands if item.name.startswith("baseline tests"))
    assert baseline.return_code == 1
    assert result.statement_coverage is not None


def test_prepare_runtime_does_not_build_dynamic_version_project(tmp_path):
    archive = tmp_path / "dynamic-version.zip"
    write_zip(
        archive,
        {
            "demo/pyproject.toml": (
                "[build-system]\n"
                'requires = ["setuptools>=61", "setuptools-scm"]\n'
                'build-backend = "setuptools.build_meta"\n\n'
                "[project]\n"
                'name = "example"\n'
                'dynamic = ["version"]\n'
            ),
            "demo/src/example/__init__.py": "def value():\n    return 1\n",
            "demo/tests/test_example.py": ("from example import value\n\ndef test_value():\n    assert value() == 1\n"),
        },
    )

    result, python = prepare_runtime(
        archive,
        tmp_path / "dynamic-runtime",
        configured_source="src",
        configured_tests="tests",
        timeout_seconds=120,
    )

    assert result.status == "runtime_ready", result.error
    assert python is not None
    resolve = next(
        (item for item in result.commands if item.name == "resolve project dependencies"),
        None,
    )
    if resolve is not None:
        assert "SETUPTOOLS_SCM_PRETEND_VERSION" not in resolve.output
        assert result.install_strategy == "uv dependency-only project resolution"
    else:
        # With no dependency manifest, the isolated venv remains the runtime
        # boundary even when the local fallback is used.
        assert result.install_strategy == "PYTHONPATH (no dependency manifest)"


def test_prepare_environment_rejects_multiple_projects_before_dependency_resolution(tmp_path):
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
        tmp_path / "must-not-be-shared",
        timeout_seconds=120,
    )

    assert python is None
    assert result.status == "runtime_failed"
    assert result.error == "Runtime preparation requires exactly one project"
    assert not result.projects


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

    def fail_resolution(result, name, command, cwd, deadline, output_limit, **kwargs):
        if name == "resolve project dependencies":
            raise RuntimeError(
                "Dependency conflict prevented this project runtime from being prepared: "
                "shared-dependency has incompatible constraints"
            )
        return original_run(result, name, command, cwd, deadline, output_limit, **kwargs)

    monkeypatch.setattr(runtime_workspace, "_run", fail_resolution)
    result, python = prepare_environment(
        [RuntimeProjectSpec("candidate", archive, "pkg", "tests")],
        tmp_path / "conflict",
        timeout_seconds=120,
    )

    assert python is None
    assert result.status == "runtime_failed"
    assert "incompatible constraints" in (result.error or "")


def test_uploaded_gepa_run_never_restores_runtime_inside_coordinator(tmp_path, monkeypatch):
    from cloud import run_job

    project_archive = tmp_path / "uploaded.zip"
    write_zip(
        project_archive,
        {
            "repo/src/actual_package/__init__.py": "VALUE = 1\n",
            "repo/tests/test_value.py": "from actual_package import VALUE\n",
        },
    )
    manifest = {
        "schema_version": 2,
        "projects": [
            {
                "kind": "uploaded",
                "project": "friendly-name",
                "archive_object": "inputs/project.zip",
                "runtime_bundle_object": "inputs/runtime.tar.gz",
                "runtime_digest": "immutable-runtime-digest",
                "runtime_image": "promptopt-runtime-py312@sha256:image",
                "runtime_worker_job": "projects/p/locations/r/jobs/eval-project",
                "source_archive_sha256": "a" * 64,
                "runtime_bundle_sha256": "b" * 64,
                "python_version": "3.12",
                "source_directory": "src",
                "test_directory": "tests",
            }
        ],
    }
    objects = {
        "inputs/dataset.jsonl": b'{"project":"friendly-name"}\n',
        "inputs/prompt.json": b"{}",
        "inputs/projects.json": json.dumps(manifest).encode(),
        # Deliberately omit the runtime bundle.  The coordinator may inspect
        # source context, but only the pinned project worker may restore and
        # execute this environment.
        "inputs/project.zip": project_archive.read_bytes(),
    }
    captured = {}

    def download(bucket, object_name, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(objects[object_name])

    def run(command):
        captured["command"] = command
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
    assert "python_executable" not in layout
    assert layout["runtime_digest"] == "immutable-runtime-digest"
    assert captured["command"][0] == sys.executable
    assert "prepare_runtime" not in " ".join(captured["command"])


def test_uploaded_gepa_run_uses_remote_worker_without_mounting_runtime_in_coordinator(tmp_path, monkeypatch):
    from cloud import run_job

    project_archive = tmp_path / "uploaded.zip"
    write_zip(
        project_archive,
        {
            "repo/src/pkg/__init__.py": "VALUE = 1\n",
            "repo/tests/test_value.py": "from pkg import VALUE\n",
        },
    )
    manifest = {
        "schema_version": 2,
        "projects": [
            {
                "kind": "uploaded",
                "project": "uploaded",
                "archive_object": "inputs/project.zip",
                "runtime_bundle_object": "inputs/runtime.tar.gz",
                "runtime_digest": "runtime-digest",
                "runtime_image": "runtime-image@sha256:one",
                "runtime_worker_job": "projects/project/locations/region/jobs/eval-project",
                "source_archive_sha256": "a" * 64,
                "runtime_bundle_sha256": "b" * 64,
                "python_version": "3.13",
                "source_directory": "src",
                "test_directory": "tests",
            }
        ],
    }
    objects = {
        "inputs/dataset.jsonl": b'{"project":"uploaded"}\n',
        "inputs/prompt.json": b"{}",
        "inputs/projects.json": json.dumps(manifest).encode(),
        "inputs/project.zip": project_archive.read_bytes(),
        # Deliberately omit runtime.tar.gz: only the independent worker may
        # restore it, never the Python 3.12 GEPA coordinator.
    }
    captured = {}

    def download(bucket, object_name, destination):
        del bucket
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(objects[object_name])

    def run(command):
        layouts_path = Path(command[command.index("--project-layouts-file") + 1])
        captured["layouts"] = json.loads(layouts_path.read_text(encoding="utf-8"))
        captured["manifest"] = os.environ.get("PROMPTOPT_EVALUATION_MANIFEST")
        captured["jobs"] = json.loads(os.environ["PROMPTOPT_EVALUATION_JOBS"])
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
        return 0, None

    monkeypatch.setattr(run_job, "_download_object", download)
    monkeypatch.setattr(run_job, "_upload_dir", lambda *args: None)
    monkeypatch.setattr(run_job, "_run_cli", run)
    monkeypatch.setenv("PROMPTOPT_CLOUD_PROJECT", "project")
    monkeypatch.setenv("PROMPTOPT_CLOUD_REGION", "region")
    monkeypatch.setenv("PROMPTOPT_EVALUATION_JOB_PY313", "eval-py313")
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
    assert "python_executable" not in captured["layouts"]["uploaded"]
    assert captured["manifest"].endswith("projects.json")
    assert captured["jobs"] == {"3.13": "projects/project/locations/region/jobs/eval-py313"}


def test_sample_gepa_remote_worker_is_pinned_in_execution_manifest(tmp_path, monkeypatch):
    from cloud import run_job

    sample_repos = tmp_path / "sample-repos"
    (sample_repos / "isort" / "isort").mkdir(parents=True)
    (sample_repos / "isort" / "tests").mkdir()
    (sample_repos / "isort" / "isort" / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    manifest = {
        "schema_version": 2,
        "projects": [
            {
                "kind": "sample",
                "project": "isort",
                "sample_slug": "isort",
                "runtime_digest": "sample:isort:commit",
                "runtime_image": "bundled-gepa-image",
                "python_version": "3.12",
                "source_directory": "isort",
                "test_directory": "tests",
            }
        ],
    }
    objects = {
        "inputs/dataset.jsonl": b'{"project":"isort"}\n',
        "inputs/prompt.json": b"{}",
        "inputs/projects.json": json.dumps(manifest).encode(),
    }
    captured = {}

    def download(bucket, object_name, destination):
        del bucket
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(objects[object_name])

    def run(command):
        effective = Path(os.environ["PROMPTOPT_EVALUATION_MANIFEST"])
        captured["manifest"] = json.loads(effective.read_text(encoding="utf-8"))
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
        return 0, None

    monkeypatch.setattr(run_job, "_download_object", download)
    monkeypatch.setattr(run_job, "_upload_dir", lambda *args: None)
    monkeypatch.setattr(run_job, "_run_cli", run)
    monkeypatch.setenv("PROMPTOPT_CLOUD_PROJECT", "project")
    monkeypatch.setenv("PROMPTOPT_CLOUD_REGION", "region")
    monkeypatch.setenv("PROMPTOPT_EVALUATION_JOB_SAMPLE", "eval-sample-deadbeef")
    monkeypatch.setenv("PROMPTOPT_SAMPLE_RUNTIME_IMAGE", "registry/gepa@sha256:abc")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_job",
            "--bucket",
            "bucket",
            "--artifacts-name",
            "runner-jobs/gepa/sample-run/artifacts",
            "--dataset-object",
            "inputs/dataset.jsonl",
            "--prompt-object",
            "inputs/prompt.json",
            "--project-manifest-object",
            "inputs/projects.json",
            "--sample-repos-dir",
            str(sample_repos),
        ],
    )

    assert run_job.main() == 0
    project = captured["manifest"]["projects"][0]
    assert project["runtime_image"] == "registry/gepa@sha256:abc"
    assert project["runtime_worker_job"].endswith("/eval-sample-deadbeef")
    assert project["runtime_digest"] != "sample:isort:commit"


def test_sample_gepa_run_keeps_bundled_layout_and_trusted_python(tmp_path, monkeypatch):
    from cloud import run_job

    sample_repos = tmp_path / "sample-repos"
    (sample_repos / "isort" / "isort").mkdir(parents=True)
    (sample_repos / "isort" / "tests").mkdir()
    objects = {
        "inputs/dataset.jsonl": b'{"project":"isort"}\n',
        "inputs/prompt.json": b"{}",
    }
    captured = {}

    def download(bucket, object_name, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(objects[object_name])

    def run(command):
        captured["command"] = command
        captured["test_python"] = os.environ.get("TESTGEN_PYTHON")
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
    monkeypatch.delenv("TESTGEN_PYTHON", raising=False)
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
            "--reflection-minibatch-size",
            "3",
            "--sample-repos-dir",
            str(sample_repos),
        ],
    )

    assert run_job.main() == 0
    command = captured["command"]
    assert command[0] == sys.executable
    assert captured["test_python"] is None
    assert "--project-layouts-file" not in command
    assert command[command.index("--reflection-minibatch-size") + 1] == "3"
    assert command[command.index("--sample-repos-dir") + 1] == str(sample_repos.resolve())
    assert command[command.index("--package-dir") + 1] == str((sample_repos / "isort" / "isort").resolve())
