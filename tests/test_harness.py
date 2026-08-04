import json
import subprocess
from pathlib import Path

import pytest

from harness.models import HarnessResult
from harness.mutation import _write_symbol_patch, parse_mutmut_results
from harness.package import add_distribution_metadata
from harness.runner import _focal_coverage, run_harness_on
from harness.sandbox import _parse_sandbox_output
from harness.workspace import docker_mount


def test_harness_result_rejects_invalid_rates():
    with pytest.raises(ValueError, match="pass_rate"):
        HarnessResult(
            build_ok=True,
            build_error="",
            num_tests=1,
            num_passed=1,
            pass_rate=1.1,
            statement_coverage=1.0,
            branch_coverage=1.0,
            mutation_score=0.0,
        )


def test_parse_sandbox_output_reads_pytest_and_coverage(tmp_path):
    (tmp_path / "report.json").write_text(
        json.dumps({"summary": {"total": 2, "passed": 1, "failed": 1}}),
        encoding="utf-8",
    )
    (tmp_path / "coverage.json").write_text(
        json.dumps(
            {
                "totals": {
                    "percent_covered": 75.0,
                    "percent_covered_branches": 50.0,
                }
            }
        ),
        encoding="utf-8",
    )
    proc = subprocess.CompletedProcess([], 1, stdout="one failed", stderr="")

    result = _parse_sandbox_output(tmp_path, proc, duration_seconds=0.25)

    assert result["build_ok"] is True
    assert result["report"]["summary"]["failed"] == 1
    assert result["coverage"]["totals"]["percent_covered"] == 75.0


def test_parse_sandbox_output_reports_collection_failure(tmp_path):
    proc = subprocess.CompletedProcess(
        [],
        2,
        stdout="ImportError while importing test module",
        stderr="",
    )

    result = _parse_sandbox_output(tmp_path, proc, duration_seconds=0.1)

    assert result["build_ok"] is False
    assert "ImportError" in result["build_error"]


def test_parse_sandbox_output_rejects_collection_error_with_json(tmp_path):
    (tmp_path / "report.json").write_text(
        json.dumps(
            {
                "summary": {"total": 0, "collected": 0},
                "collectors": [
                    {"outcome": "failed", "longrepr": "PackageNotFoundError"}
                ],
            }
        ),
        encoding="utf-8",
    )
    proc = subprocess.CompletedProcess([], 2, stdout="", stderr="")

    result = _parse_sandbox_output(tmp_path, proc, duration_seconds=0.1)

    assert result["build_ok"] is False
    assert "PackageNotFoundError" in result["build_error"]


def test_distribution_metadata_uses_pyproject_name(tmp_path):
    project = tmp_path / "project"
    package = project / "different_import_name"
    destination = tmp_path / "sandbox"
    package.mkdir(parents=True)
    destination.mkdir()
    (project / "pyproject.toml").write_text(
        '[project]\nname = "published-name"\n', encoding="utf-8"
    )

    metadata = add_distribution_metadata(package, destination)

    assert metadata.name == "published_name-0.0.0.dist-info"
    assert "Name: published-name" in (metadata / "METADATA").read_text(
        encoding="utf-8"
    )


def test_docker_mount_uses_named_volume_subpath(tmp_path, monkeypatch):
    shared = tmp_path / "shared"
    workspace = shared / "run" / "input"
    workspace.mkdir(parents=True)
    monkeypatch.setenv("TESTGEN_SHARED_WORKSPACE", str(shared))
    monkeypatch.setenv("TESTGEN_DOCKER_WORKSPACE_VOLUME", "testgen-work")

    arguments = docker_mount(workspace, "/app/input", read_only=True)

    assert arguments == [
        "--mount",
        "type=volume,src=testgen-work,dst=/app/input,"
        "volume-subpath=run/input,readonly",
    ]


def test_runner_maps_raw_result_to_contract(monkeypatch):
    monkeypatch.setattr(
        "harness.runner.run_in_sandbox",
        lambda *args, **kwargs: {
            "build_ok": True,
            "report": {"summary": {"total": 4, "passed": 3}},
            "coverage": {
                "totals": {
                    "percent_covered": 80.0,
                    "percent_covered_branches": 62.5,
                }
            },
            "duration_seconds": 1.25,
        },
    )

    result = run_harness_on("module.py", "def test_x(): pass", run_mutation=False)

    assert result.build_ok is True
    assert result.num_tests == 4
    assert result.num_passed == 3
    assert result.pass_rate == 0.75
    assert result.statement_coverage == 0.8
    assert result.branch_coverage == 0.625
    assert result.duration_seconds == 1.25


def test_focal_coverage_uses_only_symbol_lines(tmp_path):
    source = tmp_path / "module.py"
    source.write_text(
        "def target(value):\n"
        "    if value:\n"
        "        return 1\n"
        "    return 0\n\n"
        "def unrelated():\n"
        "    return 2\n",
        encoding="utf-8",
    )
    coverage = {
        "files": {
            "module.py": {
                "executed_lines": [1, 2, 3, 6, 7],
                "missing_lines": [4],
                "executed_branches": [[2, 3]],
                "missing_branches": [[2, 4]],
            }
        }
    }

    statement, branch = _focal_coverage(coverage, source, "target")

    assert statement == pytest.approx(3 / 4)
    assert branch == pytest.approx(1 / 2)


def test_runner_does_not_mutate_when_tests_fail(monkeypatch):
    monkeypatch.setattr(
        "harness.runner.run_in_sandbox",
        lambda *args, **kwargs: {
            "build_ok": True,
            "report": {"summary": {"total": 2, "passed": 1}},
            "coverage": {"totals": {}},
            "duration_seconds": 0.1,
        },
    )
    called = False

    def mutation(*args, **kwargs):
        nonlocal called
        called = True
        return 1.0, []

    monkeypatch.setattr("harness.runner.run_mutation_testing", mutation)

    result = run_harness_on("module.py", "test", run_mutation=True)

    assert result.pass_rate == 0.5
    assert called is False


def test_runner_preserves_coverage_when_mutation_times_out(monkeypatch):
    monkeypatch.setattr(
        "harness.runner.run_in_sandbox",
        lambda *args, **kwargs: {
            "build_ok": True,
            "report": {"summary": {"total": 1, "passed": 1}},
            "coverage": {
                "totals": {
                    "percent_covered": 80.0,
                    "percent_covered_branches": 60.0,
                }
            },
            "duration_seconds": 0.1,
        },
    )

    def mutation(*args, **kwargs):
        raise subprocess.TimeoutExpired("mutmut", 300)

    monkeypatch.setattr("harness.runner.run_mutation_testing", mutation)

    result = run_harness_on("module.py", "test")

    assert result.build_ok is True
    assert result.pass_rate == 1.0
    assert result.statement_coverage == 0.8
    assert result.branch_coverage == 0.6
    assert result.mutation_score == 0.0


def test_runner_scopes_mutation_to_focal_source(monkeypatch):
    monkeypatch.setattr(
        "harness.runner.run_in_sandbox",
        lambda *args, **kwargs: {
            "build_ok": True,
            "report": {"summary": {"total": 1, "passed": 1}},
            "coverage": {"totals": {}},
            "duration_seconds": 0.1,
        },
    )
    captured = {}

    def mutation(module_path, test_code, **kwargs):
        captured.update(module_path=module_path, test_code=test_code, **kwargs)
        return 0.5, [12]

    monkeypatch.setattr("harness.runner.run_mutation_testing", mutation)

    result = run_harness_on(
        "package",
        "test",
        mutation_target="package/module.py",
        mutation_symbol="target",
    )

    assert result.mutation_score == 0.5
    assert captured["mutation_target"] == "package/module.py"
    assert captured["mutation_symbol"] == "target"


def test_symbol_patch_only_marks_qualified_function_lines(tmp_path):
    source = tmp_path / "module.py"
    source.write_text(
        "def first():\n"
        "    return 1\n\n"
        "class Example:\n"
        "    def target(self, value):\n"
        "        if value:\n"
        "            return 2\n"
        "        return 3\n",
        encoding="utf-8",
    )
    patch = tmp_path / "target.patch"

    _write_symbol_patch(
        source,
        "Example.target",
        patch,
        patch_path="/work/pkg/module.py",
    )
    text = patch.read_text(encoding="utf-8")

    assert "+++ /work/pkg/module.py" in text
    assert "@@ -5,4 +5,4 @@" in text
    assert "def first" not in text


def test_parse_mutmut_results():
    output = "\n".join(
        [
            "pkg/module.py:10: x_run__mutmut_1: killed",
            "pkg/module.py:12: x_run__mutmut_2: survived",
            "pkg/module.py:12: x_run__mutmut_3: survived",
        ]
    )

    score, surviving = parse_mutmut_results(output)

    assert score == pytest.approx(1 / 3)
    assert surviving == [12]


def test_parse_mutmut_status_id_summary():
    output = "\n".join(
        [
            "MUTMUT_KILLED_IDS=1 2 3",
            "MUTMUT_SURVIVED_IDS=4",
            "MUTMUT_TIMEOUT_IDS=5",
            "MUTMUT_SUSPICIOUS_IDS=",
        ]
    )

    score, surviving = parse_mutmut_results(output)

    assert score == pytest.approx(3 / 5)
    assert surviving == []


def test_parse_current_mutmut_progress_summary():
    output = (
        "\r⠧ 7/7  🎉 7  ⏰ 0  🤔 0  🙁 0  🔇 0\n"
        "To apply a mutant on disk: mutmut apply <id>\n"
    )

    score, surviving = parse_mutmut_results(output)

    assert score == 1.0
    assert surviving == []


def test_sandbox_routes_coverage_state_to_writable_output(tmp_path, monkeypatch):
    source = tmp_path / "sample.py"
    source.write_text("def f(): return 1\n", encoding="utf-8")
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        output_mount = command[command.index("-v", command.index("-v") + 1) + 1]
        output_dir = Path(output_mount.split(":/app/output:rw")[0])
        (output_dir / "report.json").write_text(
            json.dumps({"summary": {"total": 1, "passed": 1}}),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("harness.sandbox.subprocess.run", fake_run)

    from harness.sandbox import run_in_sandbox

    result = run_in_sandbox(source, "def test_f(): assert True")

    assert result["build_ok"] is True
    assert "COVERAGE_FILE=/app/output/.coverage" in captured["command"]
    assert "--cov=sample" in captured["command"]
    assert ["-p", "no:cacheprovider"] == captured["command"][-3:-1]
