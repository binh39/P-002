from __future__ import annotations

import json
from argparse import Namespace
from types import SimpleNamespace

import pytest

from evaluation.baselines import (
    SYMPROMPT_INSTRUCTIONS,
    ZERO_SHOT_INSTRUCTIONS,
    CoverUpDirectoryGenerator,
    CoverUpManifestGenerator,
    DspyModuleGenerator,
    normalize_test_code,
)
from evaluation.cli import _require_source_upload_consent
from evaluation.holdout import build_corrected_protocol, select_fresh_holdout
from evaluation.ledger import HoldoutLedger, holdout_digest
from evaluation.models import BaselineEvaluation, GeneratedTest
from evaluation.preflight import validate_generation_contract
from evaluation.report import REQUIRED_BASELINES, generate_report
from evaluation.runner import evaluate_generator
from evaluation.statistics import paired_bootstrap
from harness.models import HarnessResult


def examples():
    return [
        SimpleNamespace(
            example_id=f"module.py::f{index}",
            module_path="module.py",
            focal_code=f"def f{index}(): return {index}",
        )
        for index in range(3)
    ]


def evaluation(name, scores):
    rows = [
        {
            "example_id": f"module.py::f{index}",
            "result": {
                "build_ok": True,
                "pass_rate": score,
                "statement_coverage": score,
                "branch_coverage": score,
                "mutation_score": score,
            },
            "cost_usd": 0.0,
            "latency_seconds": 0.1,
        }
        for index, score in enumerate(scores)
    ]
    return BaselineEvaluation(
        name=name,
        build_rate=1.0,
        pass_rate=sum(scores) / len(scores),
        statement_coverage=sum(scores) / len(scores),
        branch_coverage=sum(scores) / len(scores),
        mutation_score=sum(scores) / len(scores),
        cost_usd=0.01,
        latency_seconds=1.0,
        holdout_digest="locked",
        per_example=rows,
    )


def test_required_baselines_include_all_four_comparators_and_gepa():
    assert REQUIRED_BASELINES == (
        "zero_shot",
        "static_symprompt",
        "coverup",
        "bootstrap_few_shot",
        "gepa",
    )
    assert "execution path" in SYMPROMPT_INSTRUCTIONS
    assert "coverage" not in ZERO_SHOT_INSTRUCTIONS.lower()
    assert "module_import" in ZERO_SHOT_INSTRUCTIONS
    assert "placeholder module" in SYMPROMPT_INSTRUCTIONS


def test_dspy_generator_passes_real_import_context():
    captured = {}

    def module(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(test_code="def test_x(): assert True")

    generated = DspyModuleGenerator(module)(
        SimpleNamespace(
            module_import="isort.settings",
            target_symbol="Config.__init__",
            focal_code="def __init__(self): pass",
            existing_tests="",
            coverage_feedback="",
        )
    )

    assert generated.test_code.startswith("def test_x")
    assert captured["module_import"] == "isort.settings"
    assert captured["target_symbol"] == "Config.__init__"


def test_generation_preflight_rejects_placeholder_before_holdout(monkeypatch):
    monkeypatch.setattr(
        "evaluation.preflight.run_harness_on",
        lambda *args, **kwargs: pytest.fail("harness must not run"),
    )
    with pytest.raises(RuntimeError, match="placeholder module import"):
        validate_generation_contract(
            lambda example: GeneratedTest(
                test_code="from your_module import f\n\ndef test_f(): assert f()\n"
            ),
            [
                SimpleNamespace(
                    example_id="pkg/module.py::f",
                    focal_code="def f(): return True",
                    module_path="pkg",
                )
            ],
        )


def test_generation_preflight_requires_collected_test(monkeypatch):
    monkeypatch.setattr(
        "evaluation.preflight.run_harness_on",
        lambda *args, **kwargs: HarnessResult(
            build_ok=False,
            build_error="collection failed",
            num_tests=0,
            num_passed=0,
            pass_rate=0.0,
            statement_coverage=0.0,
            branch_coverage=0.0,
            mutation_score=0.0,
        ),
    )
    with pytest.raises(RuntimeError, match="could not collect"):
        validate_generation_contract(
            lambda example: GeneratedTest(
                test_code="from pkg.module import f\n\ndef test_f(): assert f()\n"
            ),
            [
                SimpleNamespace(
                    example_id="pkg/module.py::f",
                    focal_code="def f(): return True",
                    module_path="pkg",
                    source_path="pkg/module.py",
                    symbol="f",
                )
            ],
        )


def test_generation_preflight_returns_measured_overhead(monkeypatch):
    monkeypatch.setattr(
        "evaluation.preflight.run_harness_on",
        lambda *args, **kwargs: HarnessResult(
            build_ok=True,
            build_error="",
            num_tests=1,
            num_passed=1,
            pass_rate=1.0,
            statement_coverage=1.0,
            branch_coverage=1.0,
            mutation_score=0.0,
            duration_seconds=0.3,
        ),
    )
    cost, latency = validate_generation_contract(
        lambda example: GeneratedTest(
            test_code="from pkg.module import f\n\ndef test_f(): assert f()\n",
            cost_usd=0.02,
            latency_seconds=0.4,
        ),
        [
            SimpleNamespace(
                example_id="pkg/module.py::f",
                focal_code="def f(): return True",
                module_path="pkg",
                source_path="pkg/module.py",
                symbol="f",
            )
        ],
    )

    assert cost == 0.02
    assert latency == pytest.approx(0.7)


def test_external_llm_baseline_requires_explicit_source_upload_consent():
    with pytest.raises(RuntimeError, match="--allow-source-upload"):
        _require_source_upload_consent(
            Namespace(baseline="zero_shot", allow_source_upload=False)
        )

    _require_source_upload_consent(
        Namespace(baseline="gepa", allow_source_upload=True)
    )
    _require_source_upload_consent(
        Namespace(baseline="coverup", allow_source_upload=False)
    )


def test_normalize_test_code_extracts_markdown_python():
    assert normalize_test_code("Here:\n```python\ndef test_x():\n    assert True\n```") == (
        "def test_x():\n    assert True\n"
    )
    assert normalize_test_code("def test_y(): pass") == "def test_y(): pass\n"


def test_holdout_digest_changes_with_focal_source():
    original = examples()
    changed = examples()
    changed[0].focal_code = "def f0(): return 99"

    assert holdout_digest(original) != holdout_digest(changed)


def test_corrected_protocol_uses_fresh_deterministic_holdout():
    original_path = "eval/prompt_optimization/datasets/isort_symbols.jsonl"
    source_root = "src/sample_repo/isort"
    original = [
        json.loads(line)
        for line in open(original_path, encoding="utf-8")
        if line.strip()
    ]
    first = build_corrected_protocol(original_path, source_root)
    second = build_corrected_protocol(original_path, source_root)
    original_ids = {
        f"{row['source_file']}::{row['symbol']}" for row in original
    }
    corrected_holdout = [
        f"{row['source_file']}::{row['symbol']}"
        for row in first
        if row["split"] == "test"
    ]

    assert first == second
    assert len(first) == 40
    assert len(corrected_holdout) == 10
    assert original_ids.isdisjoint(corrected_holdout)


def test_fresh_holdout_fails_when_no_eligible_symbol(tmp_path):
    package = tmp_path / "isort"
    package.mkdir()
    (package / "small.py").write_text("def f():\n    return 1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="requires 1 eligible"):
        select_fresh_holdout(tmp_path, set(), count=1)


def test_locked_runner_saves_once_and_refuses_repeat(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "evaluation.runner.run_harness_on",
        lambda *args: HarnessResult(
            build_ok=True,
            build_error="",
            num_tests=1,
            num_passed=1,
            pass_rate=1.0,
            statement_coverage=0.8,
            branch_coverage=0.7,
            mutation_score=0.6,
            duration_seconds=0.2,
        ),
    )
    ledger = HoldoutLedger(tmp_path / "ledger.json")
    result_file = tmp_path / "zero_shot.json"

    result = evaluate_generator(
        "zero_shot",
        lambda example: GeneratedTest(
            test_code="def test_x(): assert True",
            cost_usd=0.01,
            latency_seconds=0.1,
        ),
        examples(),
        result_file=result_file,
        ledger=ledger,
    )

    assert result.mutation_score == 0.6
    assert result.cost_usd == pytest.approx(0.03)
    assert result.latency_seconds == pytest.approx(0.9)
    assert result.per_example[0]["test_code"] == "def test_x(): assert True"
    assert result_file.exists()
    with pytest.raises(RuntimeError, match="already evaluated"):
        evaluate_generator(
            "zero_shot",
            lambda example: GeneratedTest(test_code="test"),
            examples(),
            result_file=result_file,
            ledger=ledger,
        )


def test_locked_runner_includes_optimizer_overhead(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "evaluation.runner.run_harness_on",
        lambda *args: HarnessResult(
            build_ok=True,
            build_error="",
            num_tests=1,
            num_passed=1,
            pass_rate=1.0,
            statement_coverage=1.0,
            branch_coverage=1.0,
            mutation_score=1.0,
            duration_seconds=0.2,
        ),
    )
    result = evaluate_generator(
        "gepa",
        lambda example: GeneratedTest(
            test_code="def test_x(): assert True",
            cost_usd=0.01,
            latency_seconds=0.1,
        ),
        examples(),
        result_file=tmp_path / "gepa.json",
        ledger=HoldoutLedger(tmp_path / "ledger.json"),
        initial_cost_usd=0.5,
        initial_latency_seconds=2.0,
    )

    assert result.cost_usd == pytest.approx(0.53)
    assert result.latency_seconds == pytest.approx(2.9)


def test_locked_runner_resumes_without_repeating_completed_holdout(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "evaluation.runner.run_harness_on",
        lambda *args, **kwargs: HarnessResult(
            build_ok=True,
            build_error="",
            num_tests=1,
            num_passed=1,
            pass_rate=1.0,
            statement_coverage=1.0,
            branch_coverage=1.0,
            mutation_score=1.0,
        ),
    )
    calls = []

    def interrupted(example):
        calls.append(example.example_id)
        if len(calls) == 2:
            raise KeyboardInterrupt
        return GeneratedTest(test_code="def test_x(): assert True")

    result_file = tmp_path / "zero_shot.json"
    ledger = HoldoutLedger(tmp_path / "ledger.json")
    with pytest.raises(KeyboardInterrupt):
        evaluate_generator(
            "zero_shot",
            interrupted,
            examples(),
            result_file=result_file,
            ledger=ledger,
        )

    resumed_calls = []
    result = evaluate_generator(
        "zero_shot",
        lambda example: (
            resumed_calls.append(example.example_id)
            or GeneratedTest(test_code="def test_x(): assert True")
        ),
        examples(),
        result_file=result_file,
        ledger=ledger,
    )

    assert [row["example_id"] for row in result.per_example] == [
        "module.py::f0",
        "module.py::f1",
        "module.py::f2",
    ]
    assert resumed_calls == ["module.py::f1", "module.py::f2"]
    assert not (tmp_path / "zero_shot.json.partial").exists()


def test_paired_bootstrap_reports_regressions_and_improvements():
    baseline = evaluation("baseline", [0.2, 0.5, 0.8])
    candidate = evaluation("gepa", [0.4, 0.4, 0.8])

    comparison = paired_bootstrap(
        baseline,
        candidate,
        metric="mutation_score",
        samples=1000,
    )

    assert comparison.mean_delta == pytest.approx((0.2 - 0.1 + 0.0) / 3)
    assert comparison.improvements == 1
    assert comparison.regressions == 1
    assert comparison.ties == 1


def test_final_report_requires_and_renders_every_baseline(tmp_path):
    evaluations = [
        evaluation(name, [0.4, 0.5, 0.6]) for name in REQUIRED_BASELINES
    ]

    report = generate_report(evaluations, tmp_path / "report.md")

    assert "Build rate" in report
    assert "## Methodology" in report
    assert "conservative mutation score of 0" in report
    assert "paired-bootstrap CI" in report
    assert "## Four LLM modes" in report
    assert "required external-tool reference" in report
    assert "## Qualitative examples" in report
    assert "Memory/warm-start" in report
    assert all(f"| {name} |" in report for name in REQUIRED_BASELINES)


def test_final_report_rejects_mixed_holdouts(tmp_path):
    evaluations = [
        evaluation(name, [0.4, 0.5, 0.6]) for name in REQUIRED_BASELINES
    ]
    evaluations[-1] = BaselineEvaluation(
        **{**evaluations[-1].as_dict(), "holdout_digest": "different"}
    )

    with pytest.raises(ValueError, match="same locked held-out"):
        generate_report(evaluations, tmp_path / "report.md")


def test_coverup_manifest_maps_each_holdout_example_explicitly(tmp_path):
    test_file = tmp_path / "test_f.py"
    test_file.write_text("def test_f(): assert True\n", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"module.py::f0": "test_f.py"}),
        encoding="utf-8",
    )

    generated = CoverUpManifestGenerator(manifest)(
        SimpleNamespace(example_id="module.py::f0")
    )

    assert generated.test_code == "def test_f(): assert True\n"


def test_coverup_directory_combines_real_cli_outputs(tmp_path):
    (tmp_path / "test_b.py").write_text(
        "def test_b(): assert True\n", encoding="utf-8"
    )
    (tmp_path / "test_a.py").write_text(
        "def test_a(): assert True\n", encoding="utf-8"
    )

    generated = CoverUpDirectoryGenerator(tmp_path)(object())

    assert generated.test_code.index("test_a") < generated.test_code.index("test_b")
