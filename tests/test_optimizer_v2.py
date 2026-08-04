from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from harness.models import HarnessResult
from optimizer.dataset import build_v2_splits
from optimizer.evaluation import evaluate_module
from optimizer.gepa import (
    MaxIterationsStopper,
    compile_gepa,
    gepa_metric,
    result_feedback,
)
from orchestration.graph import build_optimization_graph


def result(**overrides):
    values = {
        "build_ok": True,
        "build_error": "",
        "num_tests": 2,
        "num_passed": 2,
        "pass_rate": 1.0,
        "statement_coverage": 0.8,
        "branch_coverage": 0.6,
        "mutation_score": 0.5,
        "surviving_mutant_lines": [12],
    }
    values.update(overrides)
    return HarnessResult(**values)


def test_gepa_feedback_is_grounded_in_harness_result():
    feedback = result_feedback(result())

    assert "2/2 tests pass" in feedback
    assert "branch coverage 60%" in feedback
    assert "mutation score 50%" in feedback
    assert "[12]" in feedback


def test_gepa_metric_returns_score_and_feedback(monkeypatch):
    monkeypatch.setattr("optimizer.gepa.run_harness_on", lambda *args: result())

    prediction = gepa_metric(
        SimpleNamespace(module_path="sample.py"),
        SimpleNamespace(test_code="def test_x(): assert True"),
    )

    assert prediction.score == pytest.approx(0.725)
    assert "Statement coverage 80%" in prediction.feedback


def test_compile_gepa_never_receives_holdout(monkeypatch):
    captured = {}

    class FakeGEPA:
        def __init__(self, **kwargs):
            captured["settings"] = kwargs

        def compile(self, student, *, trainset, valset):
            captured.update(student=student, trainset=trainset, valset=valset)
            return "optimized"

    monkeypatch.setattr("optimizer.gepa.dspy.GEPA", FakeGEPA)
    train = [SimpleNamespace()] * 20
    validation = [SimpleNamespace()] * 10

    optimized = compile_gepa(
        SimpleNamespace(),
        train,
        validation,
        reflection_lm=SimpleNamespace(),
        max_iterations=15,
    )

    assert optimized == "optimized"
    assert len(captured["trainset"]) == 20
    assert len(captured["valset"]) == 10
    assert captured["settings"]["metric"] is gepa_metric
    stopper = captured["settings"]["gepa_kwargs"]["stop_callbacks"][0]
    assert isinstance(stopper, MaxIterationsStopper)
    assert stopper(SimpleNamespace(i=13)) is False
    assert stopper(SimpleNamespace(i=14)) is True


def test_v2_dataset_has_fixed_disjoint_protocol():
    train, validation, holdout = build_v2_splits(
        "eval/prompt_optimization/datasets/isort_symbols.jsonl",
        "src/sample_repo/isort",
        harness_module_path="src/sample_repo/isort/isort",
    )

    assert (len(train), len(validation), len(holdout)) == (20, 10, 10)
    assert all(item.module_path.endswith("isort") for item in train + validation + holdout)
    assert all(item.module_import.startswith("isort.") for item in train + validation + holdout)
    assert all(item.target_symbol == item.symbol for item in train + validation + holdout)


def test_evaluate_module_aggregates_common_harness(monkeypatch):
    monkeypatch.setattr(
        "optimizer.evaluation.run_harness_on",
        lambda *args: result(),
    )
    def module(**kwargs):
        return SimpleNamespace(test_code="test")
    examples = [
        SimpleNamespace(
            module_path="sample.py",
            focal_code="code",
            existing_tests="",
            coverage_feedback="",
        )
        for _ in range(2)
    ]

    evaluation = evaluate_module(module, examples)

    assert evaluation.build_rate == 1.0
    assert evaluation.branch_coverage == 0.6
    assert len(evaluation.per_example) == 2


@pytest.mark.asyncio
async def test_v2_graph_runs_three_coarse_nodes(monkeypatch):
    baseline = SimpleNamespace(name="baseline")
    optimized = SimpleNamespace(name="optimized")
    monkeypatch.setattr(
        "orchestration.nodes.TestGenReactModule",
        lambda module_path, **kwargs: baseline,
    )
    monkeypatch.setattr(
        "orchestration.nodes.compile_gepa",
        lambda *args, **kwargs: optimized,
    )
    monkeypatch.setattr(
        "orchestration.nodes.experiment_span",
        lambda *args, **kwargs: nullcontext(),
    )
    graph = build_optimization_graph()

    output = await graph.ainvoke(
        {
            "experiment_id": "exp-1",
            "module_path": "sample.py",
            "trainset": [SimpleNamespace()] * 20,
            "valset": [SimpleNamespace()] * 10,
            "budget_limit_usd": 1.0,
            "reflection_lm": SimpleNamespace(),
        }
    )

    assert output["baseline_module"] is baseline
    assert output["optimized_module"] is optimized
