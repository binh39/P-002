from types import SimpleNamespace

import pytest

from harness.models import HarnessResult
from optimizer.bootstrap import compile_bootstrap
from optimizer.dataset import (
    build_examples,
    extract_focal_code,
    source_file_to_module_import,
)
from optimizer.metrics import composite_score, simple_metric
from optimizer.module import TestGenReactModule as ReactModule
from optimizer.tools import check_coverage_gaps, run_test_draft


def harness_result(**overrides):
    values = {
        "build_ok": True,
        "build_error": "",
        "num_tests": 2,
        "num_passed": 2,
        "pass_rate": 1.0,
        "statement_coverage": 0.8,
        "branch_coverage": 0.5,
        "mutation_score": 0.4,
    }
    values.update(overrides)
    return HarnessResult(**values)


def test_extract_focal_code_supports_qualified_method(tmp_path):
    source = tmp_path / "sample.py"
    source.write_text(
        "class Example:\n"
        "    def method(self, value):\n"
        "        return value + 1\n\n"
        "def other():\n"
        "    return 0\n",
        encoding="utf-8",
    )

    focal = extract_focal_code(source, "Example.method")

    assert focal.startswith("    def method")
    assert "return value + 1" in focal
    assert "def other" not in focal


def test_build_examples_sets_only_generation_inputs():
    examples = build_examples(
        [{"module_path": "sample.py", "focal_code": "def f(): pass"}]
    )

    assert len(examples) == 1
    assert set(examples[0].inputs().keys()) == {
        "module_import",
        "target_symbol",
        "focal_code",
        "existing_tests",
        "coverage_feedback",
    }
    assert examples[0].module_path == "sample.py"


def test_source_file_to_module_import_is_real_and_dotted():
    assert source_file_to_module_import("isort/settings.py") == "isort.settings"
    assert source_file_to_module_import("isort/deprecated/__init__.py") == (
        "isort.deprecated"
    )
    with pytest.raises(ValueError, match="Python source"):
        source_file_to_module_import("isort/settings.txt")


def test_composite_score_uses_documented_weights():
    result = harness_result()

    assert composite_score(result) == pytest.approx(
        0.35 + 0.35 * 0.4 + 0.20 * 0.5 + 0.10 * 0.8
    )


def test_simple_metric_executes_prediction(monkeypatch):
    captured = {}

    def fake_run(module_path, test_code):
        captured.update(module_path=module_path, test_code=test_code)
        return harness_result()

    monkeypatch.setattr("optimizer.metrics.run_harness_on", fake_run)

    score = simple_metric(
        SimpleNamespace(module_path="sample.py"),
        SimpleNamespace(test_code="def test_f(): assert True"),
    )

    assert score == pytest.approx(composite_score(harness_result()))
    assert captured["module_path"] == "sample.py"


def test_tools_return_runtime_evidence(monkeypatch):
    monkeypatch.setattr(
        "optimizer.tools.run_harness_on",
        lambda *args, **kwargs: harness_result(num_tests=3, num_passed=2, pass_rate=2 / 3),
    )

    gaps = check_coverage_gaps("sample.py", "test")
    draft = run_test_draft("sample.py", "test")

    assert "1 test(s) fail" in gaps
    assert "[ERROR] 2/3 pass" in draft


def test_react_module_owns_bounded_agent(monkeypatch, tmp_path):
    captured = {}

    class FakeReact:
        def __init__(self, signature, tools, max_iters):
            captured.update(signature=signature, tools=tools, max_iters=max_iters)

        def __call__(self, **kwargs):
            return SimpleNamespace(test_code="pass", inputs=kwargs)

    monkeypatch.setattr("optimizer.module.dspy.ReAct", FakeReact)

    module = ReactModule(tmp_path / "sample.py", max_iters=3)
    result = module("def f(): pass")

    assert captured["max_iters"] == 3
    assert len(captured["tools"]) == 2
    assert result.test_code == "pass"
    assert result.inputs["module_import"] == ""
    assert result.inputs["target_symbol"] == ""


def test_bootstrap_requires_five_to_ten_examples():
    with pytest.raises(ValueError, match="5 to 10"):
        compile_bootstrap(SimpleNamespace(), [SimpleNamespace()] * 4)


def test_bootstrap_compiles_with_simple_metric(monkeypatch):
    captured = {}

    class FakeBootstrap:
        def __init__(self, **kwargs):
            captured["settings"] = kwargs

        def compile(self, student, *, trainset):
            captured.update(student=student, trainset=trainset)
            return "compiled"

    monkeypatch.setattr("optimizer.bootstrap.dspy.BootstrapFewShot", FakeBootstrap)
    student = SimpleNamespace()

    result = compile_bootstrap(student, [SimpleNamespace()] * 5)

    assert result == "compiled"
    assert captured["settings"]["metric"] is simple_metric
    assert len(captured["trainset"]) == 5
