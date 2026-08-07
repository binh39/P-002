import asyncio
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.optimization.cli import _resolve_project_layouts, _top_isort_targets, should_promote
from src.optimization.coveragepy import (
    SymbolCoverage,
    load_report,
    run_coverage,
    symbol_coverage,
)
from src.optimization.gepa import (
    CoverUpPromptAdapter,
    build_coverage_report,
    bundle_digest,
    evaluate_bundle_cached,
    optimize,
    validate_bundle,
    validate_reference_evaluation,
    validate_template,
)
from src.optimization.metrics import aggregate_coverage_score, build_feedback, score_symbol
from src.optimization.models import ExperimentConfig, ProjectLayout, SymbolTarget
from src.optimization.prompts import PromptBundle, baseline_bundle
from src.optimization.runner import CoverUpExperimentRunner, _zero_coverage_like


def coverage(*, executed_lines=(), missing_lines=(), executed_branches=(), missing_branches=()):
    return SymbolCoverage(
        source_file="pkg/module.py",
        symbol="target",
        covered_statements=len(executed_lines),
        num_statements=len(executed_lines) + len(missing_lines),
        covered_branches=len(executed_branches),
        num_branches=len(executed_branches) + len(missing_branches),
        executed_lines=tuple(executed_lines),
        missing_lines=tuple(missing_lines),
        executed_branches=tuple(executed_branches),
        missing_branches=tuple(missing_branches),
    )


def test_zero_coverage_start_preserves_all_targets():
    after = coverage(
        executed_lines=(1, 2), missing_lines=(3,),
        executed_branches=((1, 2),), missing_branches=((1, 3),),
    )

    before = _zero_coverage_like(after)

    assert before.covered_statements == 0
    assert before.covered_branches == 0
    assert before.missing_lines == (1, 2, 3)
    assert before.missing_branches == ((1, 2), (1, 3))


def test_run_coverage_exports_zero_coverage_when_pytest_collects_no_tests(
    tmp_path, monkeypatch,
):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if "json" in command:
            Path(command[command.index("-o") + 1]).write_text(
                '{"files": {}}', encoding="utf-8"
            )
            return SimpleNamespace(
                args=command, returncode=0, stdout="json written", stderr=None
            )
        return SimpleNamespace(
            args=command,
            returncode=5,
            stdout="no tests ran",
            stderr=None,
        )

    monkeypatch.setattr("src.optimization.coveragepy.subprocess.run", fake_run)
    package_dir = tmp_path / "pkg"
    tests_dir = tmp_path / "tests"
    package_dir.mkdir()
    tests_dir.mkdir()
    output = tmp_path / "coverage.json"

    completed = run_coverage(
        project_root=tmp_path,
        package_dir=package_dir,
        tests_dir=tests_dir,
        output=output,
    )

    assert completed.returncode == 0
    assert completed.stdout == "no tests ran"
    assert output.is_file()
    assert len(calls) == 2


def test_run_coverage_does_not_mask_real_pytest_failures(tmp_path, monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(
            args=command, returncode=1, stdout="test failed", stderr=None
        )

    monkeypatch.setattr("src.optimization.coveragepy.subprocess.run", fake_run)
    package_dir = tmp_path / "pkg"
    tests_dir = tmp_path / "tests"
    package_dir.mkdir()
    tests_dir.mkdir()

    completed = run_coverage(
        project_root=tmp_path,
        package_dir=package_dir,
        tests_dir=tests_dir,
        output=tmp_path / "coverage.json",
    )

    assert completed.returncode == 1
    assert len(calls) == 1


@pytest.mark.parametrize(
    ("optimized", "baseline", "expected"),
    [(0.6, 0.5, True), (0.5, 0.5, False), (0.4, 0.5, False)],
)
def test_promotion_requires_strict_improvement(optimized, baseline, expected):
    assert should_promote(
        optimized_mean=optimized, baseline_mean=baseline
    ) is expected


def test_runner_batches_symbols_and_separates_split_workspace(tmp_path, monkeypatch):
    package_dir = tmp_path / "sample_repo" / "pkg"
    tests_dir = tmp_path / "sample_repo" / "tests"
    artifacts_dir = tmp_path / "artifacts"
    package_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)
    prompt_path = tmp_path / "prompt.json"
    baseline_bundle().save(prompt_path)
    commands = []

    def fake_subprocess_run(command, **kwargs):
        commands.append(command)
        trace_path = Path(command[command.index("--trace-file") + 1])
        trace_path.write_text(
            json.dumps({
                "source_file": "pkg/a.py",
                "symbol": "first",
                "name": "first",
                "component": "initial",
                "outcome": "coverage_gain_saved",
            }) + "\n",
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stdout="coverup ok")

    def fake_run_coverage(**kwargs):
        return SimpleNamespace(returncode=1, stdout="no generated tests")

    monkeypatch.setattr("src.optimization.runner.subprocess.run", fake_subprocess_run)
    monkeypatch.setattr("src.optimization.runner.run_coverage", fake_run_coverage)
    runner = CoverUpExperimentRunner(ExperimentConfig(
        project_root=tmp_path,
        package_dir=package_dir,
        tests_dir=tests_dir,
        artifacts_dir=artifacts_dir,
        coverup_model="fake-model",
    ))
    targets = [
        SymbolTarget("project", "pkg/a.py", "first", "train"),
        SymbolTarget("project", "pkg/b.py", "Second.method", "train"),
    ]
    stale_empty_workspace = (
        artifacts_dir / "generated_tests" / "train" / "tests_candidate_candidate"
    )
    stale_empty_workspace.mkdir(parents=True)

    record = runner.evaluate_batch(
        targets, prompt_path, candidate_id="candidate", split="train"
    )
    baseline_record = runner.evaluate_batch(
        targets,
        prompt_path,
        candidate_id="baseline",
        split="train",
        workspace_kind="baseline",
    )

    command = commands[0]
    assert command[command.index("--target-symbols") + 1] == "first,Second.method"
    target_spec = Path(command[command.index("--target-spec-file") + 1])
    assert json.loads(target_spec.read_text(encoding="utf-8")) == [
        {"source_file": "pkg/a.py", "symbol": "first"},
        {"source_file": "pkg/b.py", "symbol": "Second.method"},
    ]
    assert command[command.index("--max-concurrency") + 1] == "10"
    assert "--trace-file" in command
    assert Path(record.tests_workspace).parts[-4:] == (
        "artifacts",
        "generated_tests",
        "train",
        "tests_candidate_candidate",
    )
    assert Path(baseline_record.tests_workspace).parts[-4:] == (
        "artifacts",
        "generated_tests",
        "train",
        "tests_base_line_baseline",
    )
    assert Path(record.tests_workspace).is_dir()
    assert len(record.results) == 2
    assert record.results[0].attempt_traces[0]["component"] == "initial"
    assert record.results[1].attempt_traces == []


def test_runner_salvages_measured_scores_after_coverup_process_failure(
    tmp_path, monkeypatch,
):
    package_dir = tmp_path / "sample_repo" / "pkg"
    tests_dir = tmp_path / "sample_repo" / "tests"
    artifacts_dir = tmp_path / "artifacts"
    package_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)
    prompt_path = tmp_path / "prompt.json"
    baseline_bundle().save(prompt_path)

    monkeypatch.setattr(
        "src.optimization.runner.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1, stdout="provider returned an empty response"
        ),
    )

    def fake_run_coverage(**kwargs):
        report = {
            "files": {
                "pkg/module.py": {
                    "functions": {
                        "target": {
                            "executed_lines": [1],
                            "missing_lines": [],
                            "executed_branches": [[1, 2]],
                            "missing_branches": [],
                            "summary": {
                                "covered_lines": 1,
                                "num_statements": 1,
                                "covered_branches": 1,
                                "num_branches": 1,
                            },
                        }
                    }
                }
            }
        }
        kwargs["output"].write_text(json.dumps(report), encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="coverage ok")

    monkeypatch.setattr("src.optimization.runner.run_coverage", fake_run_coverage)
    runner = CoverUpExperimentRunner(ExperimentConfig(
        project_root=tmp_path,
        package_dir=package_dir,
        tests_dir=tests_dir,
        artifacts_dir=artifacts_dir,
        coverup_model="fake-model",
    ))

    record = runner.evaluate_batch(
        [SymbolTarget("project", "pkg/module.py", "target", "validation")],
        prompt_path,
        candidate_id="partial",
        split="validation",
    )

    score = record.results[0].score
    assert record.exit_code == 1
    assert score["score"] == 1.0
    assert score["valid"] is True
    assert score["generator_exit_code"] == 1
    assert "keeps its measured score" in record.results[0].feedback


def test_existing_baseline_tests_are_scored_without_coverup(tmp_path, monkeypatch):
    package_dir = tmp_path / "sample_repo" / "pkg"
    baseline_tests = tmp_path / "sample_repo" / "tests_baseline"
    artifacts_dir = tmp_path / "artifacts"
    package_dir.mkdir(parents=True)
    baseline_tests.mkdir(parents=True)
    (baseline_tests / "test_existing.py").write_text(
        "def test_existing(): pass\n", encoding="utf-8"
    )

    def fake_run_coverage(**kwargs):
        report = {
            "files": {
                "pkg/module.py": {
                    "functions": {
                        "target": {
                            "executed_lines": [1],
                            "missing_lines": [2],
                            "executed_branches": [[1, 2]],
                            "missing_branches": [[1, 3]],
                            "summary": {
                                "covered_lines": 1,
                                "num_statements": 2,
                                "covered_branches": 1,
                                "num_branches": 2,
                            },
                        }
                    }
                }
            }
        }
        kwargs["output"].write_text(json.dumps(report), encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="coverage ok")

    monkeypatch.setattr("src.optimization.runner.run_coverage", fake_run_coverage)
    monkeypatch.setattr(
        "src.optimization.runner.subprocess.run",
        lambda *args, **kwargs: pytest.fail("CoverUp must not be invoked"),
    )
    runner = CoverUpExperimentRunner(ExperimentConfig(
        project_root=tmp_path,
        package_dir=package_dir,
        tests_dir=tmp_path / "sample_repo" / "tests",
        artifacts_dir=artifacts_dir,
        coverup_model="fake-model",
    ))
    target = SymbolTarget("project", "pkg/module.py", "target", "validation")

    record = runner.evaluate_existing_tests_batch(
        [target], baseline_tests, split="validation"
    )

    assert record.tests_workspace == str(baseline_tests.resolve())
    assert record.results[0].score["score"] == pytest.approx(0.5)
    assert record.results[0].score["valid"] is True


def test_score_symbol_uses_statement_and_branch_gain():
    before = coverage(
        executed_lines=(1,), missing_lines=(2, 3),
        executed_branches=((1, 2),), missing_branches=((2, 3), (2, 4)),
    )
    after = coverage(
        executed_lines=(1, 2), missing_lines=(3,),
        executed_branches=((1, 2), (2, 3)), missing_branches=((2, 4),),
    )

    result = score_symbol(before, after)

    assert result.statement_gain == 0.5
    assert result.branch_gain == 0.5
    assert result.score == pytest.approx(0.5)
    assert result.gained_lines == (2,)
    assert result.gained_branches == ((2, 3),)
    assert "Remaining branches" in build_feedback(result)


def test_aggregate_score_weights_total_statements_and_branches():
    results = [
        {"score": score_symbol(coverage(missing_lines=(1,), missing_branches=((1, 2),)),
                               coverage(executed_lines=(1,), executed_branches=((1, 2),))).as_dict()},
        {"score": score_symbol(coverage(missing_lines=tuple(range(10)),
                                                missing_branches=tuple((i, i + 1) for i in range(10))),
                               coverage(missing_lines=tuple(range(10)),
                                        missing_branches=tuple((i, i + 1) for i in range(10)))).as_dict()},
    ]

    aggregate = aggregate_coverage_score(results)

    assert aggregate["statement_coverage"] == pytest.approx(1 / 11)
    assert aggregate["branch_coverage"] == pytest.approx(1 / 11)
    assert aggregate["score"] == pytest.approx(1 / 11)


def test_aggregate_score_penalizes_missing_coverage_using_reference():
    target = {
        "project": "project",
        "source_file": "pkg/module.py",
        "symbol": "target",
        "split": "validation",
    }
    reference = [{
        "target": target,
        "coverage": score_symbol(
            coverage(missing_lines=(1,), missing_branches=((1, 2),)),
            coverage(executed_lines=(1,), executed_branches=((1, 2),)),
        ).as_dict(),
    }]

    aggregate = aggregate_coverage_score(
        [{"target": target, "score": 0.0, "coverage": None}],
        reference_results=reference,
    )

    assert aggregate["score"] == 0.0
    assert aggregate["num_statements"] == 1
    assert aggregate["num_branches"] == 1


def test_isort_dataset_selects_110_targets_with_locked_holdout():
    report_path = Path("src/coverage.json")
    if not report_path.exists():
        pytest.skip("Repository coverage fixture is not present")

    targets = _top_isort_targets(report_path)

    assert len(targets) == 110
    assert sum(item["split"] == "train" for item in targets) == 50
    assert sum(item["split"] == "validation" for item in targets) == 30
    assert sum(item["split"] == "test" for item in targets) == 30
    assert all("/_vendored/" not in item["source_file"] for item in targets)
    assert targets == _top_isort_targets(report_path, seed=7)
    assert targets != _top_isort_targets(report_path, seed=8)


def test_parse_real_coverage_json_by_symbol():
    report_path = Path("src/coverage.json")
    if not report_path.exists():
        pytest.skip("Repository coverage fixture is not present")

    result = symbol_coverage(
        load_report(report_path), "isort/parse.py", "file_contents"
    )

    assert result.num_statements > 0
    assert result.num_branches > 0
    assert 0 <= result.statement_coverage <= 1
    assert 0 <= result.branch_coverage <= 1


def test_baseline_prompt_preserves_coverup_placeholders():
    bundle = baseline_bundle()
    template = bundle.initial
    assert validate_template(template) is None
    assert validate_bundle(bundle) is None
    assert "{error}" in bundle.error
    assert set(bundle.as_candidate()) == {"initial", "error"}
    rendered = template.format(
        filename="pkg/module.py",
        coverage_targets="lines 4 and 5",
        source_excerpt="def target(): pass",
    )
    assert "pkg/module.py" in rendered
    assert "lines 4 and 5" in rendered


def test_invalid_candidate_prompt_is_rejected():
    error = validate_template("Generate a test for {filename}")
    assert error is not None
    assert "coverage_targets" in error


def test_bundle_rejects_missing_repair_prompt():
    bundle = baseline_bundle()
    invalid = type(bundle)(initial=bundle.initial, error=None)
    error = validate_bundle(invalid)
    assert error is not None
    assert "error prompt" in error


def test_metric_evaluation_is_cached_per_prompt_and_symbol(tmp_path):
    class FakeRunner:
        calls = 0

        def evaluate_batch(
            self, targets, candidate, *, candidate_id=None, split=None,
            workspace_kind="candidate",
        ):
            self.calls += 1
            self.candidate_id = candidate_id
            return SimpleNamespace(
                run_id="run-1",
                tests_workspace="tests-candidate",
                results=[SimpleNamespace(
                    target=target,
                    score={"score": 0.75},
                    feedback="cached feedback",
                ) for target in targets],
            )

    runner = FakeRunner()
    target = SymbolTarget("project", "pkg/module.py", "target")
    bundle = baseline_bundle()

    first = evaluate_bundle_cached(runner, target, bundle, tmp_path)
    second = evaluate_bundle_cached(runner, target, bundle, tmp_path)

    assert first == second
    assert first["score"] == 0.75
    assert runner.calls == 1
    assert runner.candidate_id.startswith(first["prompt_digest"] + "-")


def test_metric_isolates_targets_in_parallel_and_serializes_batch_cache(tmp_path):
    class ConcurrentRunner:
        def __init__(self):
            self.config = SimpleNamespace(max_concurrency=2, rate_limit=None)
            self.active = 0
            self.max_active = 0
            self.calls = 0
            self.guard = threading.Lock()

        def evaluate_batch(
            self, targets, candidate, *, candidate_id=None, split=None,
            workspace_kind="candidate",
        ):
            with self.guard:
                self.calls += 1
                self.active += 1
                self.max_active = max(self.max_active, self.active)
            time.sleep(0.05)
            with self.guard:
                self.active -= 1
            return SimpleNamespace(
                run_id="run-batch",
                tests_workspace="tests-candidate",
                results=[SimpleNamespace(
                    target=target,
                    score={"score": 0.5},
                    feedback="ok",
                ) for target in targets],
            )

    runner = ConcurrentRunner()
    bundle = baseline_bundle()
    targets = [
        SymbolTarget("project", "pkg/a.py", "first"),
        SymbolTarget("project", "pkg/b.py", "second"),
    ]

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(
            lambda target: evaluate_bundle_cached(
                runner, target, bundle, tmp_path, targets
            ),
            targets,
        ))

    assert [result["score"] for result in results] == [0.5, 0.5]
    assert runner.max_active == 2
    assert runner.calls == 2


def test_batch_cache_and_workspace_are_separate_per_split(tmp_path):
    class SplitRunner:
        def __init__(self):
            self.calls = []

        def evaluate_batch(
            self, targets, candidate, *, candidate_id=None, split=None,
            workspace_kind="candidate",
        ):
            self.calls.append(split)
            return SimpleNamespace(
                run_id=f"run-{split}",
                tests_workspace=f"tests_candidate_{candidate_id}_{split}",
                results=[SimpleNamespace(
                    target=target,
                    score={"score": 0.25},
                    feedback=split,
                ) for target in targets],
            )

    runner = SplitRunner()
    bundle = baseline_bundle()
    train = SymbolTarget("project", "pkg/train.py", "train_target", "train")
    validation = SymbolTarget(
        "project", "pkg/validation.py", "validation_target", "validation"
    )

    train_result = evaluate_bundle_cached(runner, train, bundle, tmp_path, [train])
    validation_result = evaluate_bundle_cached(
        runner, validation, bundle, tmp_path, [validation]
    )

    assert train_result["run_id"] == "run-train"
    assert validation_result["run_id"] == "run-validation"
    assert runner.calls == ["train", "validation"]
    digest = train_result["prompt_digest"]
    assert list((tmp_path / "evaluations" / digest).glob("*/train/batch.json"))
    assert list((tmp_path / "evaluations" / digest).glob("*/validation/batch.json"))


def test_direct_gepa_adapter_returns_distinct_per_symbol_scores_and_context(tmp_path):
    project = tmp_path / "sample_repo"
    package = project / "pkg"
    package.mkdir(parents=True)
    (package / "a.py").write_text(
        "def first(value):\n    if value:\n        return 1\n    return 0\n",
        encoding="utf-8",
    )
    (package / "b.py").write_text(
        "def second(value):\n    return value + 1\n",
        encoding="utf-8",
    )

    class FakeRunner:
        def __init__(self):
            self.calls = []
            self.config = SimpleNamespace(
                package_dir=package,
                project_root=tmp_path,
            )

        def evaluate_batch(
            self, targets, candidate, *, candidate_id=None, split=None,
            workspace_kind="candidate",
        ):
            assert len(targets) == 1
            self.calls.append(candidate_id)
            results = []
            for target in targets:
                value = 0.2 if target.symbol == "first" else 0.8
                covered = int(value * 10)
                results.append(SimpleNamespace(
                    target=target,
                    score={
                        "score": value,
                        "statement_gain": value,
                        "branch_gain": value,
                        "statement_coverage": value,
                        "branch_coverage": value,
                        "covered_statements": covered,
                        "num_statements": 10,
                        "covered_branches": covered,
                        "num_branches": 10,
                        "gained_lines": [],
                        "gained_branches": [],
                        "remaining_lines": [2],
                        "remaining_branches": [[2, 4]],
                        "valid": True,
                    },
                    feedback=f"feedback for {target.symbol}",
                    attempt_traces=[{
                        "attempt": 1,
                        "component": "initial",
                        "outcome": "coverage_gain_saved",
                        "generated_test": f"def test_{target.symbol}(): pass",
                    }],
                ))
            return SimpleNamespace(
                run_id=f"run-{candidate_id}",
                tests_workspace=f"tests-{candidate_id}",
                results=results,
            )

    targets = [
        SymbolTarget("project", "pkg/a.py", "first", "train"),
        SymbolTarget("project", "pkg/b.py", "second", "train"),
    ]
    runner = FakeRunner()
    baseline = baseline_bundle()
    adapter = CoverUpPromptAdapter(
        runner=runner,
        candidate_dir=tmp_path / "candidates",
        targets_by_split={"train": targets},
        baseline=baseline,
        reflection_lm=lambda prompt: ["<template>unchanged</template>"],
        evaluation_replicates=2,
    )

    evaluated = adapter.evaluate(
        targets, baseline.as_candidate(), capture_traces=True
    )
    reflective = adapter.make_reflective_dataset(
        baseline.as_candidate(), evaluated, ["initial"]
    )

    assert evaluated.scores == pytest.approx([0.2, 0.8])
    assert len(runner.calls) == 4
    assert len(set(runner.calls)) == 4
    assert all(call.startswith(bundle_digest(baseline) + "-") for call in runner.calls)
    assert sum("-r1-" in call for call in runner.calls) == 2
    assert "pkg/a.py::first" == reflective["initial"][0]["Inputs"]["target"]
    assert "def first" in reflective["initial"][0]["Inputs"]["source_context"]
    assert (
        reflective["initial"][0]["Generated Outputs"]["component_attempts"][0]
        ["generated_test"]
        == "def test_first(): pass"
    )


def test_reflection_uses_only_attempts_from_the_component_being_optimized(tmp_path):
    baseline = baseline_bundle()
    adapter = CoverUpPromptAdapter(
        runner=SimpleNamespace(),
        candidate_dir=tmp_path,
        targets_by_split={},
        baseline=baseline,
        reflection_lm=lambda prompt: pytest.fail("no evidence must not invoke the LM"),
    )
    evaluation = SimpleNamespace(trajectories=[{
        "target": {
            "source_file": "pkg/a.py",
            "symbol": "first",
        },
        "score": 0.25,
        "replicate_scores": [0.25],
        "feedback": "missing branches",
        "source_context": "def first(): ...",
        "attempt_traces": [{
            "attempt": 1,
            "component": "error",
            "outcome": "test_error",
            "generated_test": "def test_first(): ...",
            "execution_error": "AssertionError",
        }],
    }])

    reflective = adapter.make_reflective_dataset(
        baseline.as_candidate(), evaluation, ["error", "initial"]
    )

    assert len(reflective["error"]) == 1
    assert reflective["initial"] == []
    unchanged = adapter.propose_new_texts(
        baseline.as_candidate(), reflective, ["initial"]
    )
    assert unchanged["initial"] == baseline.initial


def test_optimize_seeds_gepa_with_exact_baseline(tmp_path, monkeypatch):
    baseline = baseline_bundle()
    captured = {}

    def fake_gepa_optimize(**kwargs):
        captured.update(kwargs)
        seed = kwargs["seed_candidate"]
        return SimpleNamespace(
            best_candidate=seed,
            best_idx=0,
            candidates=[seed],
            val_aggregate_scores=[0.75],
            total_metric_calls=2,
        )

    monkeypatch.setattr("src.optimization.gepa.gepa_core.optimize", fake_gepa_optimize)
    monkeypatch.setattr(
        "src.optimization.gepa.evaluate_bundle_repeated",
        lambda runner, targets, *args, **kwargs: {
            "results": [
                {
                    "target": target.__dict__,
                    "coverage": {
                        "valid": True,
                        "num_statements": 1,
                        "num_branches": 0,
                    },
                    "feedback": "ok",
                }
                for target in targets
            ],
        },
    )
    train = [
        SymbolTarget("project", f"pkg/{index}.py", f"target_{index}", "train")
        for index in range(8)
    ]
    validation = [
        SymbolTarget("project", "pkg/b.py", "second", "validation")
    ]

    result = optimize(
        runner=SimpleNamespace(),
        train_targets=train,
        validation_targets=validation,
        baseline=baseline,
        reflection_lm=lambda prompt: [prompt],
        artifacts_dir=tmp_path,
        auto=None,
        max_metric_calls=2,
    )

    assert captured["seed_candidate"] == baseline.as_candidate()
    assert set(captured["seed_candidate"]) == {"initial", "error"}
    assert captured["cache_evaluation"] is False
    assert captured["reflection_minibatch_size"] == 8
    assert captured["module_selector"] == "round_robin"
    assert result.best_bundle == baseline


def test_tune_skips_final_split_when_gepa_keeps_unchanged_baseline(
    tmp_path, monkeypatch,
):
    from src.optimization import cli

    baseline = baseline_bundle()
    prompt_path = tmp_path / "baseline.json"
    baseline.save(prompt_path)
    artifacts = tmp_path / "artifacts"
    train = [SymbolTarget("project", "pkg/a.py", "first", "train")]
    validation = [
        SymbolTarget("project", "pkg/b.py", "second", "validation")
    ]
    test = [SymbolTarget("project", "pkg/c.py", "third", "test")]
    targets = {"train": train, "validation": validation, "test": test}

    monkeypatch.setattr(cli, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setenv("OPTIMIZE_MODEL", "vertex_ai/test-model")
    monkeypatch.setattr(
        cli,
        "make_runner",
        lambda args, projects=None: SimpleNamespace(
            config=SimpleNamespace(artifacts_dir=artifacts)
        ),
    )
    monkeypatch.setattr(cli, "load_targets", lambda path, split: targets[split])
    monkeypatch.setattr(cli.dspy, "LM", lambda *args, **kwargs: object())
    monkeypatch.setattr(
        cli,
        "optimize",
        lambda **kwargs: SimpleNamespace(
            best_bundle=baseline,
            as_dict=lambda: {
                "best_index": 0,
                "best_candidate": baseline.as_candidate(),
                "validation_scores": [0.5],
                "total_metric_calls": 1,
                "candidates": [baseline.as_candidate()],
            },
        ),
    )
    monkeypatch.setattr(
        cli,
        "evaluate_bundle_repeated",
        lambda *args, **kwargs: pytest.fail(
            "unchanged baseline must not evaluate the final split"
        ),
    )
    args = SimpleNamespace(
        project_root=tmp_path,
        artifacts_dir=artifacts,
        prompt=prompt_path,
        dataset=tmp_path / "dataset.jsonl",
        holdout_split="test",
        reflection_temperature=0.7,
        auto=None,
        max_metric_calls=1,
        evaluation_replicates=1,
        baseline_tests_dir=None,
    )

    cli.tune(args)

    report = json.loads(
        (artifacts / "final_validation.json").read_text(encoding="utf-8")
    )
    assert report["final_evaluation_skipped"] is True
    assert report["skip_reason"].startswith("GEPA selected the unchanged baseline")
    assert report["final_split"] == "test"
    assert report["run_ids"] == []
    assert report["baseline_run_ids"] == []
    assert baseline_bundle().as_candidate() == json.loads(
        (artifacts / "prompts" / "gepa_optimized.json").read_text(encoding="utf-8")
    )


def test_exact_target_spec_does_not_match_same_name_in_another_file(monkeypatch):
    import importlib

    monkeypatch.syspath_prepend(str(Path("src").resolve()))
    coverup_module = importlib.import_module("coverup.coverup")
    args = SimpleNamespace(
        target_specs={("pkg/a.py", "find")},
        target_symbols={"find"},
    )

    assert coverup_module.matches_target_spec(
        args,
        SimpleNamespace(path=Path("repo/pkg/a.py"), qualname="find", name="find"),
    )
    assert not coverup_module.matches_target_spec(
        args,
        SimpleNamespace(path=Path("repo/pkg/b.py"), qualname="find", name="find"),
    )
    assert not coverup_module.matches_target_spec(
        args,
        SimpleNamespace(
            path=Path("repo/pkg/a.py"),
            qualname="PathFinder.find",
            name="find",
        ),
    )


def test_baseline_preflight_rejects_missing_coverage_denominators():
    with pytest.raises(RuntimeError, match="Coverage lookup failed"):
        validate_reference_evaluation([{
            "target": {
                "project": "project",
                "source_file": "pkg/missing.py",
                "symbol": "target",
                "split": "validation",
            },
            "coverage": None,
            "feedback": "Replicate 0:\nScore: 0. Coverage lookup failed",
        }])


def test_coverup_retries_null_assistant_content_without_crashing(tmp_path, monkeypatch):
    import importlib

    monkeypatch.syspath_prepend(str(Path("src").resolve()))
    coverup_module = importlib.import_module("coverup.coverup")

    counters = []
    monkeypatch.setattr(
        coverup_module,
        "state",
        SimpleNamespace(inc_counter=counters.append),
        raising=False,
    )

    class EmptyChatter:
        calls = 0

        async def chat(self, messages, *, ctx=None):
            self.calls += 1
            return {
                "choices": [{
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": None},
                }]
            }

    class MinimalPrompter:
        def initial_prompt(self, seg):
            return [{"role": "user", "content": "write tests"}]

    chatter = EmptyChatter()
    result = asyncio.run(coverup_module.improve_coverage(
        SimpleNamespace(
            dry_run=False,
            max_attempts=1,
            log_file=str(tmp_path / "coverup.log"),
        ),
        chatter,
        MinimalPrompter(),
        SimpleNamespace(name="target"),
    ))

    assert result is True
    assert chatter.calls == 1
    assert counters == ["R"]
    assert "Empty assistant response" in (tmp_path / "coverup.log").read_text()


def test_coverup_trace_preserves_component_level_attempt_history(tmp_path, monkeypatch):
    import importlib
    import subprocess

    monkeypatch.syspath_prepend(str(Path("src").resolve()))
    coverup_module = importlib.import_module("coverup.coverup")
    monkeypatch.setattr(
        coverup_module,
        "state",
        SimpleNamespace(inc_counter=lambda key: None),
        raising=False,
    )
    monkeypatch.setattr(coverup_module, "test_seq", 1)

    coverage_calls = 0

    async def fake_measure_test_coverage(**kwargs):
        nonlocal coverage_calls
        coverage_calls += 1
        if coverage_calls == 1:
            raise subprocess.CalledProcessError(
                1, ["pytest"], output=b"AssertionError: wrong result"
            )
        return {
            "files": {
                "pkg/a.py": {
                    "executed_lines": [2],
                    "executed_branches": [],
                }
            }
        }

    monkeypatch.setattr(
        coverup_module, "measure_test_coverage", fake_measure_test_coverage
    )

    class Chatter:
        calls = 0

        async def chat(self, messages, *, ctx=None):
            self.calls += 1
            code = "assert False" if self.calls == 1 else "assert True"
            return {
                "choices": [{
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": f"```python\n{code}\n```",
                    },
                }]
            }

    class Prompter:
        def initial_prompt(self, seg):
            return [{"role": "user", "content": "initial instructions"}]

        def error_prompt(self, seg, error):
            return [{"role": "user", "content": f"repair: {error}"}]

    segment = SimpleNamespace(
        filename="pkg/a.py",
        qualname="first",
        name="first",
        missing_lines={2},
        missing_branches=set(),
        identify=lambda: "pkg/a.py:1-3",
    )
    args = SimpleNamespace(
        dry_run=False,
        max_attempts=3,
        log_file=str(tmp_path / "coverup.log"),
        trace_file=tmp_path / "attempt_trace.jsonl",
        install_missing_modules=False,
        pytest_args="",
        tests_dir=tmp_path,
        prefix="trace",
        isolate_tests=True,
        branch_coverage=True,
        show_details=False,
        save_coverage_to=None,
    )

    result = asyncio.run(
        coverup_module.improve_coverage(args, Chatter(), Prompter(), segment)
    )
    traces = [
        json.loads(line)
        for line in args.trace_file.read_text(encoding="utf-8").splitlines()
    ]

    assert result is True
    assert [trace["component"] for trace in traces] == ["initial", "error"]
    assert [trace["outcome"] for trace in traces] == [
        "test_error", "coverage_gain_saved",
    ]
    assert traces[0]["execution_error"] == "AssertionError: wrong result"
    assert traces[1]["generated_test"].strip() == "assert True"


def test_coverup_stops_after_no_gain_without_a_third_prompt_component(
    tmp_path, monkeypatch,
):
    import importlib

    monkeypatch.syspath_prepend(str(Path("src").resolve()))
    coverup_module = importlib.import_module("coverup.coverup")
    monkeypatch.setattr(
        coverup_module,
        "state",
        SimpleNamespace(inc_counter=lambda key: None),
        raising=False,
    )
    monkeypatch.setattr(coverup_module, "test_seq", 1)

    async def fake_measure_test_coverage(**kwargs):
        return {
            "files": {
                "pkg/a.py": {
                    "executed_lines": [],
                    "executed_branches": [],
                }
            }
        }

    monkeypatch.setattr(
        coverup_module, "measure_test_coverage", fake_measure_test_coverage
    )

    class Chatter:
        calls = 0

        async def chat(self, messages, *, ctx=None):
            self.calls += 1
            return {
                "choices": [{
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": "```python\nassert True\n```",
                    },
                }]
            }

    class Prompter:
        def initial_prompt(self, seg):
            return [{"role": "user", "content": "initial instructions"}]

        def error_prompt(self, seg, error):
            return [{"role": "user", "content": f"repair: {error}"}]

    chatter = Chatter()
    segment = SimpleNamespace(
        filename="pkg/a.py",
        qualname="first",
        name="first",
        missing_lines={2},
        missing_branches=set(),
        identify=lambda: "pkg/a.py:1-3",
    )
    args = SimpleNamespace(
        dry_run=False,
        max_attempts=3,
        log_file=str(tmp_path / "coverup.log"),
        trace_file=tmp_path / "attempt_trace.jsonl",
        install_missing_modules=False,
        pytest_args="",
        tests_dir=tmp_path,
        prefix="trace",
        isolate_tests=True,
        branch_coverage=True,
        show_details=False,
        save_coverage_to=None,
    )

    result = asyncio.run(
        coverup_module.improve_coverage(args, chatter, Prompter(), segment)
    )
    trace = json.loads(
        args.trace_file.read_text(encoding="utf-8").splitlines()[0]
    )

    assert result is True
    assert chatter.calls == 1
    assert trace["component"] == "initial"
    assert trace["outcome"] == "no_coverage_gain_unrepairable"
    assert "next_component" not in trace


def test_runner_partitions_targets_by_project(tmp_path, monkeypatch):
    alpha_pkg = tmp_path / "repos" / "alpha" / "alpha"
    beta_pkg = tmp_path / "repos" / "beta" / "beta"
    alpha_pkg.mkdir(parents=True)
    beta_pkg.mkdir(parents=True)
    artifacts_dir = tmp_path / "artifacts"
    prompt_path = tmp_path / "prompt.json"
    baseline_bundle().save(prompt_path)
    commands = []
    coverage_outputs = []

    def fake_subprocess_run(command, **kwargs):
        commands.append(command)
        trace_path = Path(command[command.index("--trace-file") + 1])
        trace_path.write_text(
            json.dumps({
                "source_file": "alpha/a.py",
                "symbol": "first",
                "name": "first",
                "component": "initial",
                "outcome": "coverage_gain_saved",
            }) + "\n",
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stdout="coverup ok")

    def fake_run_coverage(**kwargs):
        coverage_outputs.append(kwargs)
        symbol = "first" if kwargs["package_dir"] == alpha_pkg else "Second.method"
        source_file = "alpha/a.py" if symbol == "first" else "beta/b.py"
        kwargs["output"].write_text(json.dumps({
            "files": {
                source_file: {
                    "functions": {
                        symbol: {
                            "executed_lines": [1],
                            "missing_lines": [],
                            "executed_branches": [[1, 2]],
                            "missing_branches": [],
                            "summary": {
                                "covered_lines": 1,
                                "num_statements": 1,
                                "covered_branches": 1,
                                "num_branches": 1,
                            },
                        }
                    }
                }
            }
        }), encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="coverage ok")

    monkeypatch.setattr("src.optimization.runner.subprocess.run", fake_subprocess_run)
    monkeypatch.setattr("src.optimization.runner.run_coverage", fake_run_coverage)
    runner = CoverUpExperimentRunner(ExperimentConfig(
        project_root=tmp_path,
        package_dir=alpha_pkg,
        tests_dir=tmp_path / "repos" / "alpha" / "tests",
        artifacts_dir=artifacts_dir,
        coverup_model="fake-model",
        projects={
            "alpha": ProjectLayout(
                package_dir=alpha_pkg,
                tests_dir=tmp_path / "repos" / "alpha" / "tests",
            ),
            "beta": ProjectLayout(
                package_dir=beta_pkg,
                tests_dir=tmp_path / "repos" / "beta" / "tests",
            ),
        },
    ))
    targets = [
        SymbolTarget("beta", "beta/b.py", "Second.method", "train"),
        SymbolTarget("alpha", "alpha/a.py", "first", "train"),
    ]

    record = runner.evaluate_batch(
        targets, prompt_path, candidate_id="candidate", split="train"
    )

    assert len(commands) == 2
    alpha_command = next(
        command for command in commands
        if command[command.index("--target-symbols") + 1] == "first"
    )
    beta_command = next(
        command for command in commands
        if command[command.index("--target-symbols") + 1] == "Second.method"
    )
    assert Path(
        alpha_command[alpha_command.index("--package-dir") + 1]
    ).resolve() == alpha_pkg.resolve()
    assert Path(
        beta_command[beta_command.index("--package-dir") + 1]
    ).resolve() == beta_pkg.resolve()
    assert Path(
        alpha_command[alpha_command.index("--tests-dir") + 1]
    ).parts[-2:] == ("tests_candidate_candidate", "alpha")
    assert Path(
        beta_command[beta_command.index("--tests-dir") + 1]
    ).parts[-2:] == ("tests_candidate_candidate", "beta")
    assert len(coverage_outputs) == 2
    assert {
        str(kwargs["package_dir"].resolve()) for kwargs in coverage_outputs
    } == {str(alpha_pkg.resolve()), str(beta_pkg.resolve())}
    assert [result.target.symbol for result in record.results] == [
        "Second.method", "first",
    ]
    assert all(result.score["score"] == 1.0 for result in record.results)


def test_existing_baseline_tests_are_scored_per_project(tmp_path, monkeypatch):
    alpha_pkg = tmp_path / "repos" / "alpha" / "alpha"
    beta_pkg = tmp_path / "repos" / "beta" / "beta"
    baseline_tests = tmp_path / "baseline"
    (baseline_tests / "alpha").mkdir(parents=True)
    (baseline_tests / "beta").mkdir(parents=True)
    (baseline_tests / "alpha" / "test_alpha.py").write_text(
        "def test_alpha(): pass\n", encoding="utf-8"
    )
    (baseline_tests / "beta" / "test_beta.py").write_text(
        "def test_beta(): pass\n", encoding="utf-8"
    )
    artifacts_dir = tmp_path / "artifacts"
    coverage_outputs = []

    def fake_run_coverage(**kwargs):
        coverage_outputs.append(kwargs)
        symbol = "first" if kwargs["package_dir"] == alpha_pkg else "Second.method"
        source_file = "alpha/a.py" if symbol == "first" else "beta/b.py"
        kwargs["output"].write_text(json.dumps({
            "files": {
                source_file: {
                    "functions": {
                        symbol: {
                            "executed_lines": [1],
                            "missing_lines": [2],
                            "executed_branches": [[1, 2]],
                            "missing_branches": [[1, 3]],
                            "summary": {
                                "covered_lines": 1,
                                "num_statements": 2,
                                "covered_branches": 1,
                                "num_branches": 2,
                            },
                        }
                    }
                }
            }
        }), encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="coverage ok")

    monkeypatch.setattr("src.optimization.runner.run_coverage", fake_run_coverage)
    monkeypatch.setattr(
        "src.optimization.runner.subprocess.run",
        lambda *args, **kwargs: pytest.fail("CoverUp must not be invoked"),
    )
    runner = CoverUpExperimentRunner(ExperimentConfig(
        project_root=tmp_path,
        package_dir=alpha_pkg,
        tests_dir=tmp_path / "repos" / "alpha" / "tests",
        artifacts_dir=artifacts_dir,
        coverup_model="fake-model",
        projects={
            "alpha": ProjectLayout(
                package_dir=alpha_pkg,
                tests_dir=tmp_path / "repos" / "alpha" / "tests",
            ),
            "beta": ProjectLayout(
                package_dir=beta_pkg,
                tests_dir=tmp_path / "repos" / "beta" / "tests",
            ),
        },
    ))
    targets = [
        SymbolTarget("alpha", "alpha/a.py", "first", "validation"),
        SymbolTarget("beta", "beta/b.py", "Second.method", "validation"),
    ]

    record = runner.evaluate_existing_tests_batch(
        targets, baseline_tests, split="validation"
    )

    assert len(coverage_outputs) == 2
    assert {
        str(kwargs["tests_dir"].resolve()) for kwargs in coverage_outputs
    } == {str(baseline_tests.resolve() / "alpha"), str(baseline_tests.resolve() / "beta")}
    assert all(result.score["score"] == pytest.approx(0.5) for result in record.results)


def test_resolve_project_layouts_requires_multi_project(tmp_path):
    targets = [SymbolTarget("isort", "isort/a.py", "f", "train")]
    assert _resolve_project_layouts(
        tmp_path, targets, Path("src/sample_repo")
    ) is None


def test_resolve_project_layouts_builds_per_project_layouts(tmp_path):
    repos = tmp_path / "src" / "sample_repo"
    for project in ("isort", "mlxtend"):
        (repos / project / project).mkdir(parents=True)
        (repos / project / "tests").mkdir(parents=True)
    targets = [
        SymbolTarget("isort", "isort/a.py", "f", "train"),
        SymbolTarget("mlxtend", "mlxtend/b.py", "g", "validation"),
    ]

    layouts = _resolve_project_layouts(
        tmp_path, targets, Path("src/sample_repo")
    )

    assert set(layouts) == {"isort", "mlxtend"}
    assert layouts["isort"].package_dir == repos / "isort" / "isort"
    assert layouts["mlxtend"].tests_dir == repos / "mlxtend" / "tests"


def test_resolve_project_layouts_fails_when_package_missing(tmp_path):
    repos = tmp_path / "src" / "sample_repo"
    (repos / "mlxtend" / "mlxtend").mkdir(parents=True)
    (repos / "mlxtend" / "tests").mkdir(parents=True)
    targets = [
        SymbolTarget("isort", "isort/a.py", "f", "train"),
        SymbolTarget("mlxtend", "mlxtend/b.py", "g", "train"),
    ]

    with pytest.raises(FileNotFoundError, match="isort"):
        _resolve_project_layouts(tmp_path, targets, Path("src/sample_repo"))


def _fake_batch(targets, *, workspace_kind):
    statement = 0.5 if workspace_kind == "baseline" else 0.7
    branch = 0.4 if workspace_kind == "baseline" else 0.6
    return {
        "results": [{"target": target.__dict__} for target in targets],
        "aggregate": {
            "score": statement,
            "statement_coverage": statement,
            "branch_coverage": branch,
            "covered_statements": int(statement * 100),
            "num_statements": 100,
            "covered_branches": int(branch * 100),
            "num_branches": 100,
        },
    }


def test_build_coverage_report_aggregates_splits_and_prompts(monkeypatch):
    baseline = baseline_bundle()
    optimized = PromptBundle(
        initial=baseline.initial + " Tighten the generated assertions.",
        error=baseline.error,
    )
    targets = {
        "train": [SymbolTarget("isort", "isort/a.py", "f", "train")],
        "validation": [
            SymbolTarget("mlxtend", "mlxtend/b.py", "g", "validation"),
            SymbolTarget("mlxtend", "mlxtend/c.py", "h", "validation"),
        ],
    }
    calls = []

    def fake_evaluate_bundle_repeated(
        runner, batch_targets, bundle, candidate_dir, *, split,
        workspace_kind, replicates=1, reference_results=None,
    ):
        calls.append((split, workspace_kind))
        return _fake_batch(batch_targets, workspace_kind=workspace_kind)

    monkeypatch.setattr(
        "src.optimization.gepa.evaluate_bundle_repeated",
        fake_evaluate_bundle_repeated,
    )

    report = build_coverage_report(
        runner=None,
        targets_by_split=targets,
        baseline=baseline,
        optimized=optimized,
        candidate_dir=Path("."),
        evaluation_replicates=1,
    )

    assert set(report["splits"]) == {"train", "validation"}
    assert calls == [
        ("train", "baseline"),
        ("train", "candidate"),
        ("validation", "baseline"),
        ("validation", "candidate"),
    ]
    train = report["splits"]["train"]
    assert train["baseline"]["num_targets"] == 1
    assert train["baseline"]["statement_coverage"] == pytest.approx(0.5)
    assert train["optimized"]["branch_coverage"] == pytest.approx(0.6)
    assert report["splits"]["validation"]["baseline"]["num_targets"] == 2
    assert report["optimized_digest"] != report["baseline_digest"]


def test_build_coverage_report_uses_baseline_kind_for_unchanged_prompt(monkeypatch):
    baseline = baseline_bundle()
    targets = {
        "train": [SymbolTarget("isort", "isort/a.py", "f", "train")],
    }
    calls = []

    def fake_evaluate_bundle_repeated(
        runner, batch_targets, bundle, candidate_dir, *, split,
        workspace_kind, replicates=1, reference_results=None,
    ):
        calls.append((split, workspace_kind))
        return _fake_batch(batch_targets, workspace_kind=workspace_kind)

    monkeypatch.setattr(
        "src.optimization.gepa.evaluate_bundle_repeated",
        fake_evaluate_bundle_repeated,
    )

    report = build_coverage_report(
        runner=None,
        targets_by_split=targets,
        baseline=baseline,
        optimized=baseline,
        candidate_dir=Path("."),
        evaluation_replicates=1,
    )

    assert calls == [("train", "baseline"), ("train", "baseline")]
    assert report["optimized_digest"] == report["baseline_digest"]
