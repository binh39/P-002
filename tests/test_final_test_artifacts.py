import hashlib
import json
from types import SimpleNamespace

import pytest

from cloud.run_test_generation import _artifact_index, _load_prompt, _stage_projects, _workspaces_for_targets
from src.optimization.models import SymbolTarget


def test_final_test_prompt_keeps_missing_coverage_component(tmp_path):
    prompt_path = tmp_path / "prompt.json"
    expected = {
        "initial": "Generate tests for {filename}: {coverage_targets}\n{source_excerpt}",
        "error": "Repair this failure: {error}",
        "missing_coverage": "Cover the remaining targets: {missing_coverage}",
    }
    prompt_path.write_text(json.dumps(expected), encoding="utf-8")

    assert _load_prompt(prompt_path) == expected


def test_final_test_prompt_rejects_snapshot_without_missing_coverage(tmp_path):
    prompt_path = tmp_path / "prompt.json"
    prompt_path.write_text(json.dumps({"initial": "initial", "error": "error"}), encoding="utf-8")

    with pytest.raises(RuntimeError, match="missing_coverage"):
        _load_prompt(prompt_path)


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
