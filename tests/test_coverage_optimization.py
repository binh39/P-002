import asyncio
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.optimization.cli import _top_isort_targets, make_runner, parser, should_promote
from src.optimization.coveragepy import (
    SymbolCoverage,
    load_report,
    run_coverage,
    symbol_coverage,
)
from src.optimization.gepa import (
    CoverUpPromptAdapter,
    bundle_digest,
    evaluate_bundle_cached,
    optimize,
    validate_bundle,
    validate_reference_evaluation,
    validate_template,
)
from src.optimization.metrics import aggregate_coverage_score, build_feedback, score_symbol
from src.optimization.models import ExperimentConfig, SymbolTarget
from src.optimization.prompts import baseline_bundle
from src.optimization.provider import resolve_model_provider
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


def test_openai_provider_defaults_to_gpt_4o_mini():
    config = resolve_model_provider({
        "LLM_PROVIDER": "openai",
        "OPENAI_API_KEY": "test-key",
    })

    assert config.provider == "openai"
    assert config.generation_model == "openai/gpt-4o-mini"
    assert config.optimization_model == "openai/gpt-4o-mini"


def test_cli_isolates_temporary_workspaces_inside_artifacts(tmp_path, monkeypatch):
    package = tmp_path / "package"
    tests = tmp_path / "tests"
    package.mkdir()
    tests.mkdir()
    monkeypatch.setattr(
        "src.optimization.cli.resolve_model_provider",
        lambda: SimpleNamespace(generation_model="openai/gpt-4o-mini"),
    )
    args = parser().parse_args(
        [
            "--project-root",
            str(tmp_path),
            "--package-dir",
            "package",
            "--tests-dir",
            "tests",
            "--artifacts-dir",
            "artifacts",
            "evaluate",
            "--dataset",
            "dataset.jsonl",
            "--prompt",
            "prompt.json",
        ]
    )

    runner = make_runner(args)

    assert runner.config.workspace_root == tmp_path / "artifacts" / "workspaces"


def test_openai_provider_is_inferred_from_api_key():
    config = resolve_model_provider({
        "OPENAI_API_KEY": "test-key",
    })

    assert config.provider == "openai"
    assert config.generation_model == "openai/gpt-4o-mini"
    assert config.optimization_model == "openai/gpt-4o-mini"


def test_coverup_reads_unified_openai_configuration(monkeypatch):
    import importlib

    monkeypatch.syspath_prepend(str(Path("src").resolve()))
    coverup_module = importlib.import_module("coverup.coverup")

    model = coverup_module.configured_model_from_env({
        "LLM_PROVIDER": "openai",
        "LLM_MODEL": "gpt-4o-mini",
        "OPENAI_API_KEY": "test-key",
    })

    assert model == "openai/gpt-4o-mini"


def test_coverup_caps_output_tokens_to_model_limit(monkeypatch):
    import importlib

    monkeypatch.syspath_prepend(str(Path("src").resolve()))
    llm_module = importlib.import_module("coverup.llm")
    monkeypatch.setattr(
        llm_module.Chatter, "_validate_model", staticmethod(lambda model: None)
    )

    chatter = llm_module.Chatter("openai/gpt-4o-mini")

    assert chatter._request([])["max_tokens"] == 16384


@pytest.mark.asyncio
async def test_coverup_draft_runner_reports_all_failures(tmp_path, monkeypatch):
    import importlib

    monkeypatch.syspath_prepend(str(Path("src").resolve()))
    runner_module = importlib.import_module("coverup.testrunner")
    captured = {}

    async def fake_subprocess_run(command, **kwargs):
        captured["command"] = command
        report = Path(command[command.index("--out") + 1])
        report.write_text("{}", encoding="utf-8")
        return SimpleNamespace(stdout=b"")

    monkeypatch.setattr(runner_module, "subprocess_run", fake_subprocess_run)

    await runner_module.measure_test_coverage(
        test="def test_example():\n    assert True\n",
        tests_dir=tmp_path,
    )

    pytest_args = captured["command"][
        captured["command"].index("pytest") + 1:
    ]
    assert "-x" not in pytest_args
    assert "--basetemp" in pytest_args
    basetemp = Path(pytest_args[pytest_args.index("--basetemp") + 1])
    assert basetemp.name == "pytest"
    assert basetemp.parent.name.startswith("coverup_pytest_")


def test_coverup_salvages_passing_top_level_tests(monkeypatch):
    import importlib

    monkeypatch.syspath_prepend(str(Path("src").resolve()))
    coverup_module = importlib.import_module("coverup.coverup")
    test_code = (
        "def test_passes():\n"
        "    assert True\n\n"
        "def test_fails():\n"
        "    assert False\n"
    )
    pytest_output = (
        "_____________________ test_fails _____________________\n"
        "E   assert False\n"
    )

    salvaged = coverup_module.remove_failing_test_functions(
        test_code, pytest_output
    )

    assert salvaged is not None
    assert "test_passes" in salvaged
    assert "test_fails" not in salvaged


def test_coverup_rejects_module_scope_mutation_of_imported_state(monkeypatch):
    import importlib

    monkeypatch.syspath_prepend(str(Path("src").resolve()))
    coverup_module = importlib.import_module("coverup.coverup")
    test_code = (
        "import isort.comments\n\n"
        "def fake_add_to_line(*args):\n"
        "    return 'changed'\n\n"
        "isort.comments.add_to_line = fake_add_to_line\n\n"
        "def test_example():\n"
        "    assert True\n"
    )

    mutations = coverup_module.find_module_scope_state_mutations(test_code)

    assert mutations == ["line 6: isort.comments.add_to_line"]


def test_coverup_allows_monkeypatch_inside_test(monkeypatch):
    import importlib

    monkeypatch.syspath_prepend(str(Path("src").resolve()))
    coverup_module = importlib.import_module("coverup.coverup")
    test_code = (
        "import isort.comments\n\n"
        "def test_example(monkeypatch):\n"
        "    monkeypatch.setattr(isort.comments, 'add_to_line', lambda *args: 'changed')\n"
        "    assert True\n"
    )

    assert coverup_module.find_module_scope_state_mutations(test_code) == []


def test_openai_provider_requires_api_key():
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        resolve_model_provider({
            "LLM_PROVIDER": "openai",
            "LLM_MODEL": "gpt-4o-mini",
        })


def test_vertex_provider_qualifies_model():
    config = resolve_model_provider({
        "LLM_PROVIDER": "vertex_ai",
        "LLM_MODEL": "gemini-test-model",
        "VERTEXAI_PROJECT": "test-project",
        "VERTEXAI_LOCATION": "global",
    })

    assert config.provider == "vertex_ai"
    assert config.generation_model == "vertex_ai/gemini-test-model"
    assert config.optimization_model == "vertex_ai/gemini-test-model"


def test_legacy_role_specific_models_remain_supported():
    config = resolve_model_provider({
        "COVERUP_MODEL": "vertex_ai/gemini-generation",
        "OPTIMIZE_MODEL": "vertex_ai/gemini-reflection",
    })

    assert config.generation_model == "vertex_ai/gemini-generation"
    assert config.optimization_model == "vertex_ai/gemini-reflection"


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
    pytest_command = calls[0]
    assert "--basetemp" in pytest_command
    basetemp = Path(pytest_command[pytest_command.index("--basetemp") + 1])
    assert basetemp.name == "pytest"
    assert basetemp.parent.name.startswith("testgen_pytest_")


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
    stale_empty_workspace = tests_dir.parent / "tests_candidate_candidate_train"
    stale_empty_workspace.mkdir()

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
    assert command[command.index("--max-concurrency") + 1] == "10"
    assert record.tests_workspace.endswith("tests_candidate_candidate_train")
    assert baseline_record.tests_workspace.endswith("tests_base_line_baseline_train")
    assert Path(record.tests_workspace).is_dir()
    assert len(record.results) == 2


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


def test_isort_dataset_selects_top_45_with_locked_holdout():
    report_path = Path("src/coverage.json")
    if not report_path.exists():
        pytest.skip("Repository coverage fixture is not present")

    targets = _top_isort_targets(report_path)

    assert len(targets) == 45
    assert sum(item["split"] == "train" for item in targets) == 25
    assert sum(item["split"] == "validation" for item in targets) == 10
    assert sum(item["split"] == "test" for item in targets) == 10
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
    assert "{missing_coverage}" in bundle.missing_coverage
    rendered = template.format(
        filename="pkg/module.py",
        missing_coverage="lines 4 and 5",
        source_excerpt="def target(): pass",
    )
    assert "pkg/module.py" in rendered
    assert "lines 4 and 5" in rendered


def test_invalid_candidate_prompt_is_rejected():
    error = validate_template("Generate a test for {filename}")
    assert error is not None
    assert "missing_coverage" in error


def test_bundle_rejects_missing_repair_prompt():
    bundle = baseline_bundle()
    invalid = type(bundle)(initial=bundle.initial, error=None, missing_coverage=None)
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


def test_metric_serializes_concurrent_targets_for_same_candidate(tmp_path):
    class ConcurrentRunner:
        def __init__(self):
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
    assert runner.max_active == 1
    assert runner.calls == 1


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
    assert len(runner.calls) == 2
    assert all(call.startswith(bundle_digest(baseline) + "-") for call in runner.calls)
    assert runner.calls[1] == runner.calls[0] + "-r1"
    assert "pkg/a.py::first" == reflective["initial"][0]["Inputs"]["target"]
    assert "def first" in reflective["initial"][0]["Inputs"]["source_context"]


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
    train = [SymbolTarget("project", "pkg/a.py", "first", "train")]
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
    assert "stop_callbacks" not in captured
    assert result.best_bundle == baseline


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
