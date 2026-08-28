import hashlib
import io
import os
import subprocess
import zipfile
from types import SimpleNamespace

from cloud import run_test_generation
from cloud.run_test_generation import _artifact_index, _run_remote, _stage_projects, _workspaces_for_targets
from src.optimization.models import SymbolTarget


def test_prompt_snapshot_accepts_gepa_missing_coverage_component(tmp_path):
    prompt = tmp_path / "prompt.json"
    prompt.write_text(
        '{"initial":"{source_excerpt}","error":"{error}",'
        '"missing_coverage":"{missing_coverage}"}',
        encoding="utf-8",
    )

    assert run_test_generation._load_prompt_snapshot(prompt)["missing_coverage"] == "{missing_coverage}"


def test_prompt_snapshot_keeps_legacy_two_component_compatibility(tmp_path):
    prompt = tmp_path / "prompt.json"
    prompt.write_text('{"initial":"initial","error":"error"}', encoding="utf-8")

    assert run_test_generation._load_prompt_snapshot(prompt) == {"initial": "initial", "error": "error"}


def test_runtime_object_download_verifies_generation_and_checksum(tmp_path, monkeypatch):
    payload = b"immutable runtime input"
    calls = []

    class Blob:
        generation = "42"

        def reload(self):
            calls.append("reload")

    class Bucket:
        def blob(self, name):
            assert name == "runtime/object"
            return Blob()

    def download(_bucket, _object_name, path):
        calls.append("download")
        path.write_bytes(payload)

    monkeypatch.setattr(run_test_generation, "_download_object", download)
    destination = tmp_path / "runtime.tar.gz"
    run_test_generation._download_verified_runtime_object(
        Bucket(),
        "runtime/object",
        destination,
        expected_sha256=hashlib.sha256(payload).hexdigest(),
        expected_generation="42",
    )
    assert calls == ["reload", "download"]


def test_runtime_object_download_rejects_changed_checksum(tmp_path, monkeypatch):
    destination = tmp_path / "runtime.tar.gz"
    monkeypatch.setattr(
        run_test_generation,
        "_download_object",
        lambda _bucket, _object_name, path: path.write_bytes(b"tampered"),
    )
    try:
        run_test_generation._download_verified_runtime_object(
            object(),
            "runtime/object",
            destination,
            expected_sha256=hashlib.sha256(b"original").hexdigest(),
        )
    except RuntimeError as exc:
        assert "checksum changed" in str(exc)
    else:
        raise AssertionError("tampered runtime object was accepted")


def test_final_test_artifact_index_contains_generated_tests_source_and_coverage(tmp_path):
    artifacts = tmp_path / "artifacts"
    generated = artifacts / "generated_tests" / "tests_candidate" / "test_parse.py"
    coverage = artifacts / "coverage" / "isort.json"
    source = artifacts / "source" / "sample_isort" / "isort" / "parse.py"
    ignored = artifacts / "generated_tests" / "notes.txt"
    generated.parent.mkdir(parents=True)
    coverage.parent.mkdir(parents=True)
    source.parent.mkdir(parents=True)
    generated.write_text("def test_parse():\n    assert True\n", encoding="utf-8")
    coverage.write_text('{"totals": {}}', encoding="utf-8")
    source.write_text("def parse():\n    return True\n", encoding="utf-8")
    ignored.write_text("not a test artifact", encoding="utf-8")

    result = _artifact_index(artifacts, [generated], [source])

    assert [(entry["id"], entry["kind"], entry["path"]) for entry in result] == [
        ("generated-test-1", "generated_test", "generated_tests/tests_candidate/test_parse.py"),
        ("source-1", "source", "source/sample_isort/isort/parse.py"),
        ("coverage-1", "coverage", "coverage/isort.json"),
    ]
    assert result[0]["content_type"] == "text/x-python"
    assert result[0]["size_bytes"] == len(generated.read_bytes())
    assert result[0]["sha256"] == hashlib.sha256(generated.read_bytes()).hexdigest()
    assert result[1]["content_type"] == "text/x-python"
    assert result[1]["size_bytes"] == len(source.read_bytes())
    assert result[1]["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert result[2]["content_type"] == "application/json"
    assert result[2]["size_bytes"] == len(coverage.read_bytes())
    assert result[2]["sha256"] == hashlib.sha256(coverage.read_bytes()).hexdigest()


def test_final_test_workspaces_are_derived_from_symbol_targets(tmp_path):
    workspace = tmp_path / "generated_tests"
    single = _workspaces_for_targets(
        [SymbolTarget(project="isort", source_file="isort/api.py", symbol="sort_file", split="final")], str(workspace)
    )
    multiple = _workspaces_for_targets(
        [
            SymbolTarget(project="isort", source_file="isort/api.py", symbol="sort_file", split="final"),
            SymbolTarget(project="mimesis", source_file="mimesis/__init__.py", symbol="x", split="final"),
        ],
        str(workspace),
    )

    assert single == {"isort": workspace}
    assert multiple == {"isort": workspace / "isort", "mimesis": workspace / "mimesis"}


def test_bundled_sample_projects_get_independent_layouts(tmp_path):
    sample_repos = tmp_path / "sample_repo"
    for project in ("isort", "mlxtend", "typesystem"):
        (sample_repos / project / project).mkdir(parents=True)
        (sample_repos / project / "tests").mkdir()

    staged_root, layouts = _stage_projects(
        SimpleNamespace(sample_repos_dir=str(sample_repos), project_manifest_object=None),
        tmp_path / "scratch",
        ["isort", "mlxtend", "typesystem"],
    )

    assert staged_root == sample_repos.resolve()
    assert set(layouts) == {"isort", "mlxtend", "typesystem"}
    assert layouts["mlxtend"].package_dir == (sample_repos / "mlxtend" / "mlxtend").resolve()
    assert layouts["typesystem"].tests_dir == (sample_repos / "typesystem" / "tests").resolve()


def test_cloud_final_generation_merges_independent_project_workers(tmp_path, monkeypatch):
    objects: dict[str, bytes] = {}

    def worker_archive(project: str) -> bytes:
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr(
                "generated_tests/test_generated.py",
                f"def test_{project}():\n    assert True\n",
            )
            archive.writestr("source/pkg/module.py", "VALUE = 1\n")
            archive.writestr("coverage/project.json", '{"totals": {}}')
        return output.getvalue()

    class Backend:
        def __init__(self, *, manifest, **kwargs):
            del kwargs
            self.projects = {item["project"]: item for item in manifest["projects"]}

        def generate_final_project(self, project, targets, prompt, *, seed):
            del prompt, seed
            object_name = f"workers/{project}.zip"
            objects[object_name] = worker_archive(project)
            return {
                "artifact_object": object_name,
                "result": {
                    "schema_version": 2,
                    "status": "completed",
                    "metrics": {
                        "target_covered_statements": 3,
                        "target_statement_count": 4,
                        "target_covered_branches": 1,
                        "target_branch_count": 2,
                        "target_count": len(targets),
                        "completed_target_count": len(targets),
                        "failed_target_count": 0,
                        "test_count": 1,
                    },
                    "estimated_cost_usd": 0.01,
                    "token_usage": {"prompt_tokens": 10},
                    "cost_accounting": {
                        "priced_request_count": 1,
                        "unpriced_request_count": 0,
                        "by_model": {},
                    },
                    "projects": {
                        project: {
                            "pytest_exit_code": 0,
                            "project_statement_coverage": 0.75,
                            "project_branch_coverage": 0.5,
                        }
                    },
                    "artifacts": {
                        "files": [
                            {"kind": "generated_test", "path": "generated_tests/test_generated.py"},
                            {"kind": "source", "path": "source/pkg/module.py"},
                            {"kind": "coverage", "path": "coverage/project.json"},
                        ]
                    },
                },
            }

    def download(bucket, object_name, destination):
        del bucket
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(objects[object_name])

    monkeypatch.setattr(run_test_generation, "RemoteEvaluationBackend", Backend)
    monkeypatch.setattr(run_test_generation, "_download_object", download)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    prompt = scratch / "prompt.json"
    prompt.write_text('{"initial":"a","error":"b"}', encoding="utf-8")
    targets = [
        SymbolTarget("one", "pkg/a.py", "a", "final"),
        SymbolTarget("two", "pkg/b.py", "b", "final"),
    ]
    manifest = {
        "schema_version": 2,
        "projects": [
            {"kind": "uploaded", "project": "one", "runtime_digest": "digest-one"},
            {"kind": "uploaded", "project": "two", "runtime_digest": "digest-two"},
        ],
    }
    args = SimpleNamespace(
        bucket="bucket",
        artifacts_name="runs/final",
        model="model",
        max_attempts=2,
        repeat_tests=1,
        max_concurrency=2,
        rate_limit=None,
        pytest_args="",
        evaluation_worker_timeout_seconds=600,
        seed=7,
    )

    result = _run_remote(args, artifacts, scratch, prompt, targets, manifest, {})

    assert result["status"] == "completed"
    assert result["metrics"]["target_count"] == 2
    assert result["metrics"]["target_statement_coverage"] == 0.75
    assert result["metrics"]["target_branch_coverage"] == 0.5
    assert result["estimated_cost_usd"] == 0.02
    assert result["prompt_digest"] == hashlib.sha256(prompt.read_bytes()).hexdigest()
    assert result["runtime"]["projects"]["one"]["runtime_digest"] == "digest-one"
    assert (artifacts / "generated_tests" / "one" / "test_generated.py").is_file()
    assert (artifacts / "generated_tests" / "two" / "test_generated.py").is_file()
    assert (artifacts / "generated_tests.zip").is_file()


def test_final_suite_coverage_uses_assigned_project_interpreter(tmp_path, monkeypatch):
    package = tmp_path / "project" / "pkg"
    package.mkdir(parents=True)
    (package / "module.py").write_text("def value():\n    return 1\n", encoding="utf-8")
    tests = tmp_path / "project" / "tests"
    tests.mkdir()
    workspace = tmp_path / "artifacts" / "generated_tests"
    runtime_python = tmp_path / "runtime" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    runtime_python.parent.mkdir(parents=True)
    runtime_python.write_bytes(b"runtime-python")
    captured: dict[str, str] = {}

    class FakeRunner:
        def __init__(self, _config):
            pass

        def evaluate_batch(self, targets, _prompt, **_kwargs):
            workspace.mkdir(parents=True, exist_ok=True)
            (workspace / "test_generated.py").write_text("def test_generated():\n    assert True\n", encoding="utf-8")
            return type(
                "Batch",
                (),
                {
                    "results": [
                        type(
                            "TargetResult",
                            (),
                            {
                                "score": {
                                    "valid": True,
                                    "covered_statements": 1,
                                    "num_statements": 1,
                                    "covered_branches": 0,
                                    "num_branches": 0,
                                    "tests_passed": True,
                                },
                                "attempt_traces": [],
                            },
                        )()
                        for _ in targets
                    ],
                    "tests_workspace": str(workspace),
                },
            )()

    def fake_run_coverage(**kwargs):
        captured.update({key: kwargs["env"][key] for key in ("TESTGEN_PYTHON", "VIRTUAL_ENV", "PATH")})
        output = kwargs["output"]
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            '{"totals":{"num_statements":1,"covered_lines":1,"num_branches":0,"covered_branches":0}}',
            encoding="utf-8",
        )
        return subprocess.CompletedProcess([], 0)

    monkeypatch.setattr(run_test_generation, "CoverUpExperimentRunner", FakeRunner)
    monkeypatch.setattr(run_test_generation, "run_coverage", fake_run_coverage)
    from src.optimization.models import ExperimentConfig, ProjectLayout

    target = SymbolTarget("uploaded", "pkg/module.py", "value", "final")
    config = ExperimentConfig(
        project_root=tmp_path / "project",
        package_dir=package,
        tests_dir=tests,
        artifacts_dir=tmp_path / "artifacts",
        coverup_model="model",
        projects={
            "uploaded": ProjectLayout(
                package_dir=package,
                tests_dir=tests,
                import_root=package.parent,
                python_executable=runtime_python,
            )
        },
    )
    prompt = tmp_path / "prompt.json"
    prompt.write_text('{"initial":"a","error":"b"}', encoding="utf-8")

    result = run_test_generation.generate_local_project(
        artifacts=tmp_path / "artifacts",
        prompt_path=prompt,
        targets=[target],
        config=config,
        sample_repos=tmp_path / "samples",
        seed=7,
    )

    assert result["status"] == "completed"
    assert captured["TESTGEN_PYTHON"] == str(runtime_python.resolve())
    assert captured["VIRTUAL_ENV"] == str(runtime_python.parent.parent.resolve())
    assert captured["PATH"].split(os.pathsep)[0] == str(runtime_python.parent.resolve())
