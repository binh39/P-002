from __future__ import annotations

import hashlib
import io
import json
import os
import tarfile
import zipfile
from pathlib import Path

import pytest

from cloud.run_evaluation_worker import _execute, _relocate_venv_scripts, _stage_project
from src.optimization.models import ProjectLayout


class _Blob:
    def __init__(self, values: dict[str, bytes], name: str):
        self.values = values
        self.name = name

    def download_to_filename(self, destination: str) -> None:
        Path(destination).write_bytes(self.values[self.name])

    def upload_from_filename(self, source: str, content_type: str | None = None) -> None:
        del content_type
        self.values[self.name] = Path(source).read_bytes()


class _GenerationBlob(_Blob):
    generation = "7"

    def reload(self, *args, **kwargs):
        del args, kwargs


class _Bucket:
    def __init__(self, values: dict[str, bytes]):
        self.values = values

    def blob(self, name: str) -> _Blob:
        return _Blob(self.values, name)


class _GenerationBucket(_Bucket):
    def blob(self, name: str) -> _Blob:
        return _GenerationBlob(self.values, name)


def _zip_bytes(files: dict[str, str]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return output.getvalue()


def _runtime_bytes() -> bytes:
    output = io.BytesIO()
    executable = "Scripts/python.exe" if os.name == "nt" else "bin/python"
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        content = b"prepared-python"
        info = tarfile.TarInfo(f".venv/{executable}")
        info.size = len(content)
        archive.addfile(info, io.BytesIO(content))
    return output.getvalue()


def test_sample_worker_enforces_pinned_image_and_job(tmp_path, monkeypatch):
    samples = tmp_path / "samples"
    package = samples / "isort" / "isort"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    monkeypatch.setenv("PROMPTOPT_SAMPLE_REPOS_DIR", str(samples))
    monkeypatch.setenv("PROMPTOPT_RUNTIME_IMAGE", "image@sha256:one")
    monkeypatch.setenv("PROMPTOPT_RUNTIME_WORKER_JOB", "projects/p/locations/r/jobs/sample-one")
    request = {
        "project": "isort",
        "project_spec": {
            "kind": "sample",
            "project": "isort",
            "sample_slug": "isort",
            "source_directory": "isort",
            "test_directory": "tests",
            "runtime_digest": "digest",
            "runtime_image": "image@sha256:one",
            "runtime_worker_job": "projects/p/locations/r/jobs/sample-one",
        },
    }

    _, layout = _stage_project(_Bucket({}), request, tmp_path / "worker")
    assert layout.runtime_digest == "digest"
    assert layout.python_executable is not None

    request["project_spec"]["runtime_image"] = "image@sha256:other"
    with pytest.raises(RuntimeError, match="Runtime image changed"):
        _stage_project(_Bucket({}), request, tmp_path / "wrong-image")


def test_restored_venv_console_script_shebang_is_relocated(tmp_path):
    python = tmp_path / "runtime" / ".venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_bytes(b"binary")
    script = python.parent / "project-cli"
    script.write_bytes(b"#!/old/build/path/.venv/bin/python\nprint('ok')\n")

    _relocate_venv_scripts(python)

    assert script.read_bytes().startswith(f"#!{python}\n".encode())


def test_worker_rejects_request_when_deployment_identity_is_not_pinned(tmp_path, monkeypatch):
    monkeypatch.delenv("PROMPTOPT_RUNTIME_IMAGE", raising=False)
    monkeypatch.delenv("PROMPTOPT_RUNTIME_WORKER_JOB", raising=False)
    request = {
        "project": "isort",
        "project_spec": {
            "kind": "sample",
            "project": "isort",
            "runtime_image": "image@sha256:one",
            "runtime_worker_job": "projects/p/locations/r/jobs/sample-one",
        },
    }

    with pytest.raises(RuntimeError, match="immutable runtime image identity"):
        _stage_project(_Bucket({}), request, tmp_path / "worker")


def test_uploaded_worker_rejects_changed_source_archive(tmp_path, monkeypatch):
    archive = _zip_bytes(
        {
            "repo/src/pkg/__init__.py": "VALUE = 1\n",
            "repo/tests/test_pkg.py": "from pkg import VALUE\n",
        }
    )
    runtime = _runtime_bytes()
    monkeypatch.setenv("PROMPTOPT_RUNTIME_IMAGE", "image@sha256:one")
    monkeypatch.setenv("PROMPTOPT_RUNTIME_WORKER_JOB", "projects/p/locations/r/jobs/uploaded-one")
    request = {
        "project": "uploaded",
        "project_spec": {
            "kind": "uploaded",
            "project": "uploaded",
            "archive_object": "project.zip",
            "runtime_bundle_object": "runtime.tar.gz",
            "runtime_protocol_version": 13,
            "execution_mode": "generic_worker_bundle",
            "runtime_digest": "digest",
            "runtime_image": "image@sha256:one",
            "runtime_worker_job": "projects/p/locations/r/jobs/uploaded-one",
            "source_archive_sha256": hashlib.sha256(b"different").hexdigest(),
            "runtime_bundle_sha256": hashlib.sha256(runtime).hexdigest(),
            "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
            "source_directory": "src",
            "test_directory": "tests",
        },
    }

    with pytest.raises(RuntimeError, match="archive no longer matches"):
        _stage_project(
            _Bucket({"project.zip": archive, "runtime.tar.gz": runtime}),
            request,
            tmp_path / "worker",
        )


def test_uploaded_worker_rejects_changed_object_generation(tmp_path, monkeypatch):
    archive = _zip_bytes({"repo/src/pkg/__init__.py": "VALUE = 1\n"})
    runtime = _runtime_bytes()
    job = "projects/p/locations/r/jobs/uploaded-one"
    monkeypatch.setenv("PROMPTOPT_RUNTIME_IMAGE", "image@sha256:one")
    monkeypatch.setenv("PROMPTOPT_RUNTIME_WORKER_JOB", job)
    request = {
        "project": "uploaded",
        "project_spec": {
            "kind": "uploaded",
            "project": "uploaded",
            "archive_object": "project.zip",
            "runtime_bundle_object": "runtime.tar.gz",
            "runtime_protocol_version": 13,
            "execution_mode": "generic_worker_bundle",
            "runtime_digest": "digest",
            "runtime_image": "image@sha256:one",
            "runtime_worker_job": job,
            "source_archive_sha256": hashlib.sha256(archive).hexdigest(),
            "runtime_bundle_sha256": hashlib.sha256(runtime).hexdigest(),
            "source_archive_generation": "8",
            "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
        },
    }
    with pytest.raises(RuntimeError, match="object generation changed"):
        _stage_project(_GenerationBucket({"project.zip": archive, "runtime.tar.gz": runtime}), request, tmp_path / "worker")


def test_uploaded_worker_restores_only_matching_runtime_capsule(tmp_path, monkeypatch):
    archive = _zip_bytes(
        {
            "repo/src/pkg/__init__.py": "VALUE = 1\n",
            "repo/tests/test_pkg.py": "from pkg import VALUE\n",
        }
    )
    runtime = _runtime_bytes()
    job = "projects/p/locations/r/jobs/uploaded-one"
    monkeypatch.setenv("PROMPTOPT_RUNTIME_IMAGE", "image@sha256:one")
    monkeypatch.setenv("PROMPTOPT_RUNTIME_WORKER_JOB", job)
    request = {
        "project": "uploaded",
        "project_spec": {
            "kind": "uploaded",
            "project": "uploaded",
            "archive_object": "project.zip",
            "runtime_bundle_object": "runtime.tar.gz",
            "runtime_digest": "digest",
            "runtime_image": "image@sha256:one",
            "runtime_worker_job": job,
            "source_archive_sha256": hashlib.sha256(archive).hexdigest(),
            "runtime_bundle_sha256": hashlib.sha256(runtime).hexdigest(),
            "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
            "source_directory": "src",
            "test_directory": "tests",
        },
    }

    root, layout = _stage_project(
        _Bucket({"project.zip": archive, "runtime.tar.gz": runtime}),
        request,
        tmp_path / "worker",
    )

    assert root.name == "repo"
    assert layout.package_dir.name == "src"
    assert layout.python_executable is not None and layout.python_executable.is_file()
    assert layout.runtime_digest == "digest"


def test_protocol_12_worker_uses_only_artifacts_baked_into_its_own_image(tmp_path, monkeypatch):
    archive = _zip_bytes(
        {
            "repo/src/pkg/__init__.py": "VALUE = 1\n",
            "repo/tests/test_pkg.py": "from pkg import VALUE\n",
        }
    )
    runtime = _runtime_bytes()
    baked_archive = tmp_path / "baked-project.zip"
    baked_bundle = tmp_path / "baked-runtime.tar.gz"
    baked_archive.write_bytes(archive)
    baked_bundle.write_bytes(runtime)
    image = f"repo/project@sha256:{'a' * 64}"
    job = "projects/p/locations/r/jobs/uploaded-project-digest"
    monkeypatch.setenv("PROMPTOPT_RUNTIME_IMAGE", image)
    monkeypatch.setenv("PROMPTOPT_RUNTIME_WORKER_JOB", job)
    monkeypatch.setenv("PROMPTOPT_BAKED_SOURCE_ARCHIVE", str(baked_archive))
    monkeypatch.setenv("PROMPTOPT_BAKED_RUNTIME_BUNDLE", str(baked_bundle))
    request = {
        "project": "uploaded",
        "project_spec": {
            "kind": "uploaded",
            "project": "uploaded",
            "archive_object": "must-not-be-downloaded.zip",
            "runtime_bundle_object": "must-not-be-downloaded.tar.gz",
            "runtime_protocol_version": 12,
            "runtime_digest": "digest",
            "runtime_image": image,
            "runtime_worker_job": job,
            "source_archive_sha256": hashlib.sha256(archive).hexdigest(),
            "runtime_bundle_sha256": hashlib.sha256(runtime).hexdigest(),
            "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
            "source_directory": "src",
            "test_directory": "tests",
        },
    }

    root, layout = _stage_project(_Bucket({}), request, tmp_path / "worker")

    assert root.name == "repo"
    assert layout.package_dir.name == "src"
    assert layout.python_executable is not None and layout.python_executable.is_file()


def test_protocol_12_worker_rejects_an_image_without_baked_artifacts(tmp_path, monkeypatch):
    image = f"repo/project@sha256:{'a' * 64}"
    job = "projects/p/locations/r/jobs/uploaded-project-digest"
    monkeypatch.setenv("PROMPTOPT_RUNTIME_IMAGE", image)
    monkeypatch.setenv("PROMPTOPT_RUNTIME_WORKER_JOB", job)
    monkeypatch.delenv("PROMPTOPT_BAKED_SOURCE_ARCHIVE", raising=False)
    monkeypatch.delenv("PROMPTOPT_BAKED_RUNTIME_BUNDLE", raising=False)
    request = {
        "project": "uploaded",
        "project_spec": {
            "kind": "uploaded",
            "project": "uploaded",
            "archive_object": "project.zip",
            "runtime_bundle_object": "runtime.tar.gz",
            "runtime_protocol_version": 12,
            "runtime_digest": "digest",
            "runtime_image": image,
            "runtime_worker_job": job,
            "source_archive_sha256": "a" * 64,
            "runtime_bundle_sha256": "b" * 64,
            "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
            "source_directory": "src",
            "test_directory": "tests",
        },
    }

    with pytest.raises(RuntimeError, match="does not contain its admitted source"):
        _stage_project(_Bucket({}), request, tmp_path / "worker")


def test_final_generation_runs_inside_the_assigned_project_worker(tmp_path, monkeypatch):
    from cloud import run_evaluation_worker, run_test_generation

    project_root = tmp_path / "project"
    package = project_root / "pkg"
    tests = project_root / "tests"
    package.mkdir(parents=True)
    tests.mkdir()
    (package / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    prompt = json.dumps({"initial": "initial", "error": "error"}).encode()
    values = {"prompt.json": prompt}
    bucket = _Bucket(values)
    captured = {}

    monkeypatch.setattr(
        run_evaluation_worker,
        "_stage_project",
        lambda *_args: (
            project_root,
            ProjectLayout(
                package_dir=package,
                tests_dir=tests,
                import_root=project_root,
                python_executable=Path(os.sys.executable),
                runtime_digest="runtime-digest",
            ),
        ),
    )

    def generate(**kwargs):
        captured.update(kwargs)
        generated = kwargs["artifacts"] / "generated_tests" / "test_generated.py"
        generated.parent.mkdir(parents=True)
        generated.write_text("def test_generated():\n    assert True\n", encoding="utf-8")
        return {"status": "succeeded", "project": "uploaded", "targets": 1}

    monkeypatch.setattr(run_test_generation, "generate_local_project", generate)
    request = {
        "schema_version": 1,
        "operation": "final_generation",
        "project": "uploaded",
        "project_spec": {"project": "uploaded"},
        "prompt_object": "prompt.json",
        "artifact_object": "worker-artifacts.zip",
        "targets": [
            {
                "project": "uploaded",
                "source_file": "pkg/__init__.py",
                "symbol": "VALUE",
                "split": "test",
            }
        ],
        "seed": 13,
        "config": {
            "coverup_model": "model",
            "max_attempts": 1,
            "repeat_tests": 1,
            "max_concurrency": 1,
            "pytest_args": "",
        },
    }

    result = _execute(bucket, request, tmp_path / "execution")

    assert result["final_generation"]["status"] == "succeeded"
    assert result["artifact_object"] == "worker-artifacts.zip"
    assert values["worker-artifacts.zip"].startswith(b"PK")
    assert captured["seed"] == 13
    assert {target.project for target in captured["targets"]} == {"uploaded"}
