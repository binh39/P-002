import asyncio
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.optimization.cli import (
    _repeat_final_baseline,
    _resolve_project_layouts,
    _top_isort_targets,
    parser,
    should_promote,
)
from src.optimization.coveragepy import (
    SymbolCoverage,
    load_report,
    run_coverage,
    symbol_coverage,
)
from src.optimization.failures import classify_attempt_failure
from src.optimization.gepa import (
    STRATEGY_PLAYBOOK_BEGIN,
    STRATEGY_PLAYBOOK_END,
    BestParetoCandidateSelector,
    CausalReflectionComponentSelector,
    CoverUpPromptAdapter,
    LLMReflectionComponentSelector,
    _evaluation_digest,
    build_coverage_report,
    bundle_digest,
    evaluate_bundle_batch_cached,
    evaluate_bundle_cached,
    log_reflection_request,
    optimize,
    rerank_prompt_candidates,
    validate_bundle,
    validate_reference_evaluation,
    validate_template,
)
from src.optimization.metrics import aggregate_coverage_score, build_feedback, score_symbol
from src.optimization.models import ExperimentConfig, ProjectLayout, SymbolTarget
from src.optimization.prompts import PromptBundle, baseline_bundle
from src.optimization.runner import (
    CoverUpExperimentRunner,
    _saved_tests_for_target,
    _test_environment,
    _traces_for_target,
    _zero_coverage_like,
)
from src.optimization.subprocesses import run_streamed


def tool_call_response(
    component,
    replacements,
    *,
    diagnosis="root cause",
    evidence=None,
    playbooks=None,
    strategy_delta=None,
):
    default_playbook = {
        "observations": ["Branch failures expose missing precondition analysis."],
        "decision_steps": [
            "Identify the uncovered behavior and its preconditions.",
            "Construct a deterministic test and assert observable behavior.",
        ],
        "failure_modes": ["Do not produce tests without meaningful assertions."],
        "regression_guards": ["Preserve already-correct tests and required output format."],
    }
    arguments = {
        "component": component,
        "replacements": replacements,
        "diagnosis": diagnosis,
        "evidence": evidence or ["observed failure"],
        "playbooks": playbooks or {
            name: dict(default_playbook) for name in replacements
        },
        "strategy_delta": strategy_delta or {
            "added": ["Analyze branch preconditions before generating tests."],
            "refined": [],
            "preserved": ["Keep deterministic tests and meaningful assertions."],
            "pruned": [],
        },
    }
    return [{
        "text": None,
        "tool_calls": [{
            "type": "function",
            "function": {
                "name": "update_prompt_component",
                "arguments": json.dumps(arguments),
            },
        }],
    }]


def test_coverup_runtime_hides_playbook_markers_and_does_not_expand_its_fields_twice(
    tmp_path,
    monkeypatch,
):
    import importlib

    monkeypatch.syspath_prepend(str(Path("src").resolve()))
    prompter_class = importlib.import_module(
        "coverup.prompt.gpt_v2"
    ).GptV2Prompter
    prompt_path = tmp_path / "prompt.json"
    prompt_path.write_text(
        json.dumps({
            "initial": (
                "Generate tests for {filename}.\n{source_excerpt}\n"
                f"{STRATEGY_PLAYBOOK_BEGIN}\n"
                "Preserve {filename}, {coverage_targets}, and {source_excerpt}.\n"
                f"{STRATEGY_PLAYBOOK_END}"
            ),
            "error": (
                "Repair this failure:\n{error}\n"
                f"{STRATEGY_PLAYBOOK_BEGIN}\n"
                "Preserve the required {error} field.\n"
                f"{STRATEGY_PLAYBOOK_END}"
            ),
        }),
        encoding="utf-8",
    )
    prompter = prompter_class(SimpleNamespace(prompt_template_file=prompt_path))

    initial = prompter._render(
        "initial",
        "",
        filename="UNIQUE_FILE.py",
        coverage_targets="UNIQUE_TARGETS",
        source_excerpt="UNIQUE_SOURCE_BODY",
    )
    error = prompter._render("error", "", error="UNIQUE_TRACEBACK")

    assert STRATEGY_PLAYBOOK_BEGIN not in initial
    assert STRATEGY_PLAYBOOK_END not in initial
    assert initial.count("UNIQUE_FILE.py") == 1
    assert initial.count("UNIQUE_SOURCE_BODY") == 1
    assert "{filename}, {coverage_targets}, and {source_excerpt}" in initial
    assert STRATEGY_PLAYBOOK_BEGIN not in error
    assert STRATEGY_PLAYBOOK_END not in error
    assert error.count("UNIQUE_TRACEBACK") == 1
    assert "{error}" in error


def test_target_context_includes_exact_contract_relevant_test_and_fixture(
    tmp_path,
    monkeypatch,
):
    import importlib

    monkeypatch.syspath_prepend(str(Path("src").resolve()))
    code_segment = importlib.import_module("coverup.segment").CodeSegment
    build_target_context = importlib.import_module(
        "coverup.target_context"
    ).build_target_context
    source_path = tmp_path / "pkg" / "service.py"
    tests_dir = tmp_path / "tests"
    source_path.parent.mkdir()
    tests_dir.mkdir()
    source_path.write_text(
        """class Base:
    pass

class Service(Base):
    @classmethod
    def parse(cls, value: str, *, strict: bool = False) -> int:
        \"\"\"Parse one value.\"\"\"
        return int(value) if strict else 0
""",
        encoding="utf-8",
    )
    (tests_dir / "test_service.py").write_text(
        """from pkg.service import Service

def test_parse(sample_value):
    assert Service.parse(sample_value, strict=True) == 3
""",
        encoding="utf-8",
    )
    (tests_dir / "conftest.py").write_text(
        """import pytest

@pytest.fixture
def sample_value():
    return \"3\"
""",
        encoding="utf-8",
    )
    segment = code_segment(
        source_path,
        "parse",
        5,
        9,
        "Service.parse",
        {8},
        {8},
        set(),
        set(),
        [(4, 5)],
        [],
    )

    context = build_target_context(segment, tests_dir, max_chars=6_000)

    assert "[TARGET CONTRACT]" in context
    assert "def Service.parse(cls, value: str, *, strict: bool=False) -> int" in context
    assert "Decorators: @classmethod" in context
    assert "Enclosing classes: Service(Base)" in context
    assert "test from test_service.py" in context
    assert "fixture from conftest.py" in context
    assert "def sample_value" in context


def test_target_context_respects_hard_character_budget(tmp_path, monkeypatch):
    import importlib

    monkeypatch.syspath_prepend(str(Path("src").resolve()))
    code_segment = importlib.import_module("coverup.segment").CodeSegment
    build_target_context = importlib.import_module(
        "coverup.target_context"
    ).build_target_context
    source_path = tmp_path / "module.py"
    source_path.write_text(
        "def target(value: str) -> str:\n    return value\n",
        encoding="utf-8",
    )
    segment = code_segment(
        source_path, "target", 1, 3, "target", {2}, {2}, set(), set(), [], []
    )

    context = build_target_context(segment, max_chars=100)

    assert len(context) <= 100
    assert context.endswith("[END TARGET CONTEXT]")


def test_failure_context_retrieves_constructor_callee_and_matching_usage(
    tmp_path,
    monkeypatch,
):
    import importlib

    monkeypatch.syspath_prepend(str(Path("src").resolve()))
    code_segment = importlib.import_module("coverup.segment").CodeSegment
    build_failure_context = importlib.import_module(
        "coverup.target_context"
    ).build_failure_context
    project_root = tmp_path / "project"
    source_path = project_root / "pkg" / "selector.py"
    test_path = project_root / "pkg" / "tests" / "test_selector.py"
    source_path.parent.mkdir(parents=True)
    test_path.parent.mkdir(parents=True)
    source_path.write_text(
        """class Selector:
    def __init__(self, estimator, scoring=None):
        self.estimator = estimator
        self.scoring = scoring

    def _score(self, values):
        return len(values)

    def fit(self, values):
        if self.scoring is None and not hasattr(self.estimator, "_estimator_type"):
            raise AttributeError("Estimator requires ._estimator_type")
        return self._score(values)
""",
        encoding="utf-8",
    )
    test_path.write_text(
        """class ValidEstimator:
    _estimator_type = "classifier"

def test_selector_fit_uses_classifier_protocol():
    selector = Selector(ValidEstimator())
    assert selector.fit([1, 2]) == 2
""",
        encoding="utf-8",
    )
    segment = code_segment(
        source_path,
        "fit",
        9,
        12,
        "Selector.fit",
        {9, 10, 11, 12},
        {9, 10, 11, 12},
        set(),
        set(),
        [],
        [],
    )

    context = build_failure_context(
        segment,
        "E AttributeError: Estimator requires ._estimator_type",
        project_root=project_root,
        max_chars=4_000,
    )

    assert "[FAILURE-TRIGGERED CONTEXT]" in context
    assert "Failure family: attribute/protocol" in context
    assert "def Selector.__init__(self, estimator, scoring=None)" in context
    assert "Selector._score" in context
    assert "test_selector_fit_uses_classifier_protocol" in context
    assert '_estimator_type = "classifier"' in context
    assert context.index("[FAILURE-RELEVANT USAGE EXAMPLES]") < context.index(
        "[DIRECT CALLEE CONTRACT]"
    )
    assert len(context) <= 4_000
    assert context.endswith("[END FAILURE-TRIGGERED CONTEXT]")


def test_gpt_v2_failure_context_is_opt_in_and_bounded(tmp_path, monkeypatch):
    import importlib

    monkeypatch.syspath_prepend(str(Path("src").resolve()))
    code_segment = importlib.import_module("coverup.segment").CodeSegment
    prompter_class = importlib.import_module(
        "coverup.prompt.gpt_v2"
    ).GptV2Prompter
    source_path = tmp_path / "pkg" / "module.py"
    source_path.parent.mkdir(parents=True)
    source_path.write_text(
        "def target(value):\n    return value\n",
        encoding="utf-8",
    )
    template = tmp_path / "prompt.json"
    template.write_text(
        json.dumps({"initial": "{source_excerpt}", "error": "ERROR={error}"}),
        encoding="utf-8",
    )
    segment = code_segment(
        source_path, "target", 1, 2, "target", {1, 2}, {1, 2}, set(), set(), [], []
    )
    disabled = prompter_class(SimpleNamespace(
        prompt_template_file=template,
        failure_context=False,
    ))
    enabled = prompter_class(SimpleNamespace(
        prompt_template_file=template,
        failure_context=True,
        failure_context_root=tmp_path,
        failure_context_max_chars=300,
    ))

    disabled_prompt = disabled.error_prompt(segment, "AssertionError")[0]["content"]
    enabled_prompt = enabled.error_prompt(segment, "AssertionError")[0]["content"]

    assert disabled_prompt == "ERROR=AssertionError"
    assert enabled_prompt.startswith("ERROR=AssertionError")
    assert "[FAILURE-TRIGGERED CONTEXT]" in enabled_prompt
    assert len(enabled_prompt) <= len("ERROR=AssertionError\n\n") + 300
    assert enabled_prompt.endswith("[END FAILURE-TRIGGERED CONTEXT]")


def test_failure_context_highlights_exact_pytest_regex_mismatch(tmp_path, monkeypatch):
    import importlib

    monkeypatch.syspath_prepend(str(Path("src").resolve()))
    code_segment = importlib.import_module("coverup.segment").CodeSegment
    build_failure_context = importlib.import_module(
        "coverup.target_context"
    ).build_failure_context
    source_path = tmp_path / "module.py"
    source_path.write_text("def target():\n    return 1\n", encoding="utf-8")
    segment = code_segment(
        source_path, "target", 1, 2, "target", {1, 2}, {1, 2}, set(), set(), [], []
    )

    context = build_failure_context(
        segment,
        "E AssertionError: Regex pattern did not match.\n"
        "E Expected regex: 'group-mates must be specified'\n"
        "E Actual message: 'group-matesmust be specified.'",
        project_root=tmp_path,
        max_chars=4_000,
    )

    assert "[ASSERTION EVIDENCE]" in context
    assert "Observed runtime message (exact): 'group-matesmust be specified.'" in context
    assert "re.escape(observed_message)" in context
    if "[FAILURE-RELEVANT USAGE EXAMPLES]" in context:
        assert context.index("[ASSERTION EVIDENCE]") < context.index(
            "[FAILURE-RELEVANT USAGE EXAMPLES]"
        )


def test_gpt_v2_appends_context_without_changing_prompt_template_contract(
    tmp_path,
    monkeypatch,
):
    import importlib

    monkeypatch.syspath_prepend(str(Path("src").resolve()))
    code_segment = importlib.import_module("coverup.segment").CodeSegment
    prompter_class = importlib.import_module("coverup.prompt.gpt_v2").GptV2Prompter
    source_path = tmp_path / "pkg" / "module.py"
    tests_dir = tmp_path / "tests"
    source_path.parent.mkdir()
    tests_dir.mkdir()
    source_path.write_text(
        "def target(value: int) -> int:\n    return value + 1\n",
        encoding="utf-8",
    )
    (tests_dir / "test_module.py").write_text(
        "def test_target():\n    assert target(1) == 2\n",
        encoding="utf-8",
    )
    template = tmp_path / "prompt.json"
    template.write_text(
        json.dumps({
            "initial": "File={filename}\nMissing={coverage_targets}\n{source_excerpt}",
            "error": "{error}",
        }),
        encoding="utf-8",
    )
    prompter = prompter_class(SimpleNamespace(
        prompt_template_file=template,
        src_base_dir=tmp_path,
        target_context=True,
        target_context_max_chars=6_000,
        context_tests_dir=tests_dir,
    ))
    segment = code_segment(
        source_path, "target", 1, 3, "target", {2}, {2}, set(), set(), [], []
    )

    prompt = prompter.initial_prompt(segment)[0]["content"]

    assert prompt.count(f"File={Path('pkg/module.py')}") == 1
    assert "Signature: def target(value: int) -> int" in prompt
    assert "test from test_module.py" in prompt
    assert "[END TARGET CONTEXT]" in prompt


def test_evaluation_digest_changes_when_repository_test_context_changes(tmp_path):
    package_dir = tmp_path / "repo" / "pkg"
    tests_dir = tmp_path / "repo" / "tests"
    package_dir.mkdir(parents=True)
    tests_dir.mkdir()
    (package_dir / "module.py").write_text(
        "def target():\n    return 1\n",
        encoding="utf-8",
    )
    repository_test = tests_dir / "test_module.py"
    repository_test.write_text("def test_target():\n    pass\n", encoding="utf-8")
    runner = CoverUpExperimentRunner(ExperimentConfig(
        project_root=tmp_path,
        package_dir=package_dir,
        tests_dir=tests_dir,
        artifacts_dir=tmp_path / "artifacts",
        coverup_model="fake-model",
    ))
    targets = [SymbolTarget("project", "pkg/module.py", "target", "train")]

    before = _evaluation_digest(runner, targets)
    repository_test.write_text(
        "def test_target():\n    assert True\n",
        encoding="utf-8",
    )
    after = _evaluation_digest(runner, targets)

    assert before != after


def test_evaluation_digest_changes_when_failure_context_is_enabled(tmp_path):
    package_dir = tmp_path / "repo" / "pkg"
    tests_dir = tmp_path / "repo" / "tests"
    package_dir.mkdir(parents=True)
    tests_dir.mkdir()
    (package_dir / "module.py").write_text(
        "def target():\n    return 1\n",
        encoding="utf-8",
    )
    runner = CoverUpExperimentRunner(ExperimentConfig(
        project_root=tmp_path,
        package_dir=package_dir,
        tests_dir=tests_dir,
        artifacts_dir=tmp_path / "artifacts",
        coverup_model="fake-model",
    ))
    targets = [SymbolTarget("project", "pkg/module.py", "target", "train")]

    before = _evaluation_digest(runner, targets)
    runner.config.failure_context = True
    runner.config.failure_context_max_chars = 3_500
    after = _evaluation_digest(runner, targets)

    assert before != after


def test_evaluation_digest_changes_when_test_salvage_is_enabled(tmp_path):
    package_dir = tmp_path / "repo" / "pkg"
    tests_dir = tmp_path / "repo" / "tests"
    package_dir.mkdir(parents=True)
    tests_dir.mkdir()
    (package_dir / "module.py").write_text(
        "def target():\n    return 1\n",
        encoding="utf-8",
    )
    runner = CoverUpExperimentRunner(ExperimentConfig(
        project_root=tmp_path,
        package_dir=package_dir,
        tests_dir=tests_dir,
        artifacts_dir=tmp_path / "artifacts",
        coverup_model="fake-model",
    ))
    targets = [SymbolTarget("project", "pkg/module.py", "target", "train")]

    before = _evaluation_digest(runner, targets)
    runner.config.salvage_failing_tests = True
    runner.config.salvage_max_prunes = 5
    after = _evaluation_digest(runner, targets)

    assert before != after


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


def test_test_environment_fixes_python_hash_seed(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTHONHASHSEED", "random")

    environment = _test_environment(tmp_path)

    assert environment["PYTHONHASHSEED"] == "0"


def test_trace_mapping_distinguishes_same_symbol_in_different_source_files(tmp_path):
    workspace = tmp_path / "shared-tests"
    workspace.mkdir()
    first_test = workspace / "test_opt_1.py"
    second_test = workspace / "test_opt_2.py"
    first_test.write_text("def test_first(): pass\n", encoding="utf-8")
    second_test.write_text("def test_second(): pass\n", encoding="utf-8")
    traces = [
        {
            "source_file": "pkg/a.py",
            "symbol": "find",
            "name": "find",
            "generated_test": "first feedback payload",
            "saved_test": str(first_test),
        },
        {
            "source_file": "pkg/b.py",
            "symbol": "find",
            "name": "find",
            "generated_test": "second feedback payload",
            "saved_test": str(second_test),
        },
    ]
    target = SymbolTarget("project", "pkg/b.py", "find", "train")

    target_traces = _traces_for_target(traces, target)
    target_tests = _saved_tests_for_target(
        traces, target, workspace=workspace,
    )

    assert [trace["generated_test"] for trace in target_traces] == [
        "second feedback payload"
    ]
    assert target_tests == [second_test.resolve()]


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

    monkeypatch.setattr("src.optimization.coveragepy.run_streamed", fake_run)
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
        repeat_tests=2,
    )
    assert completed.returncode == 0
    assert completed.stdout == "no tests ran"
    assert output.is_file()
    assert len(calls) == 2
    assert calls[0][calls[0].index("--count") + 1] == "2"


def test_run_coverage_collects_only_explicit_target_test_paths(tmp_path, monkeypatch):
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
            args=command, returncode=5, stdout="no tests ran", stderr=None
        )

    monkeypatch.setattr("src.optimization.coveragepy.run_streamed", fake_run)
    package_dir = tmp_path / "pkg"
    tests_dir = tmp_path / "shared-tests"
    pytest_temp_root = tmp_path / "pytest-temp"
    package_dir.mkdir()
    tests_dir.mkdir()
    selected = tests_dir / "test_for_one_target.py"
    ignored = tests_dir / "test_for_another_target.py"
    selected.write_text("def test_selected(): pass\n", encoding="utf-8")
    ignored.write_text("def test_ignored(): pass\n", encoding="utf-8")
    pytest_basetemp = pytest_temp_root / "target"

    run_coverage(
        project_root=tmp_path,
        package_dir=package_dir,
        tests_dir=tests_dir,
        test_paths=[selected],
        pytest_basetemp=pytest_basetemp,
        output=tmp_path / "coverage.json",
    )

    pytest_command = calls[0]
    assert str(selected.resolve()) in pytest_command
    assert str(ignored.resolve()) not in pytest_command
    assert str(tests_dir.resolve()) not in pytest_command
    assert pytest_command[pytest_command.index("-p") + 1] == "no:cacheprovider"
    assert pytest_command[pytest_command.index("--basetemp") + 1] == str(
        pytest_basetemp.resolve()
    )


def test_parallel_coverage_subprocesses_use_isolated_pytest_state(tmp_path):
    package_dir = tmp_path / "pkg"
    tests_dir = tmp_path / "shared-tests"
    pytest_temp_root = tmp_path / "pytest-temp"
    package_dir.mkdir()
    tests_dir.mkdir()
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "module.py").write_text(
        "def first(value):\n    return value + 1\n\n"
        "def second(value):\n    return value * 2\n",
        encoding="utf-8",
    )
    first_test = tests_dir / "test_first.py"
    second_test = tests_dir / "test_second.py"
    first_test.write_text(
        "from pkg.module import first\n\n"
        "def test_first(tmp_path):\n"
        "    assert tmp_path.is_dir()\n"
        "    assert first(1) == 2\n",
        encoding="utf-8",
    )
    second_test.write_text(
        "from pkg.module import second\n\n"
        "def test_second(tmp_path):\n"
        "    assert tmp_path.is_dir()\n"
        "    assert second(2) == 4\n",
        encoding="utf-8",
    )

    def execute_target(name, test_path):
        return run_coverage(
            project_root=tmp_path,
            package_dir=package_dir,
            tests_dir=tests_dir,
            test_paths=[test_path],
            pytest_basetemp=pytest_temp_root / name,
            output=tmp_path / f"coverage-{name}.json",
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(execute_target, "first", first_test),
            executor.submit(execute_target, "second", second_test),
        ]
        completed = [future.result(timeout=30) for future in futures]

    assert [result.returncode for result in completed] == [0, 0]
    assert (tmp_path / "coverage-first.json").is_file()
    assert (tmp_path / "coverage-second.json").is_file()
    assert (pytest_temp_root / "first").is_dir()
    assert (pytest_temp_root / "second").is_dir()
    assert not (tests_dir / ".pytest_cache").exists()
    assert not (tests_dir / "__pycache__").exists()
    assert not (package_dir / "__pycache__").exists()


def test_optimization_cli_defaults_to_five_test_repetitions():
    args = parser().parse_args([
        "evaluate", "--dataset", "dataset.jsonl", "--prompt", "prompt.json",
    ])

    assert args.repeat_tests == 5
    assert args.target_context is True
    assert args.target_context_max_chars == 6_000
    assert args.repository_test_context is False
    assert args.failure_context is False
    assert args.failure_context_max_chars == 4_000
    assert args.salvage_failing_tests is False
    assert args.salvage_max_prunes == 8


def test_optimization_cli_can_disable_and_bound_target_context():
    args = parser().parse_args([
        "--no-target-context",
        "--target-context-max-chars",
        "2500",
        "--no-repository-test-context",
        "evaluate",
        "--dataset",
        "dataset.jsonl",
        "--prompt",
        "prompt.json",
    ])

    assert args.target_context is False
    assert args.target_context_max_chars == 2_500
    assert args.repository_test_context is False


def test_optimization_cli_can_enable_and_bound_failure_context():
    args = parser().parse_args([
        "--failure-context",
        "--failure-context-max-chars",
        "3500",
        "evaluate",
        "--dataset",
        "dataset.jsonl",
        "--prompt",
        "prompt.json",
    ])

    assert args.failure_context is True
    assert args.failure_context_max_chars == 3_500


def test_optimization_cli_can_enable_and_bound_test_salvage():
    args = parser().parse_args([
        "--salvage-failing-tests",
        "--salvage-max-prunes",
        "5",
        "evaluate",
        "--dataset",
        "dataset.jsonl",
        "--prompt",
        "prompt.json",
    ])

    assert args.salvage_failing_tests is True
    assert args.salvage_max_prunes == 5


def test_optimization_cli_exposes_gepa_search_controls():
    args = parser().parse_args([
        "optimize",
        "--dataset",
        "dataset.jsonl",
        "--prompt",
        "prompt.json",
        "--max-metric-calls",
        "30",
        "--gepa-seed",
        "19",
        "--reflection-minibatch-size",
        "3",
        "--best-candidate-probability",
        "0.5",
        "--rerank-top-k",
        "5",
        "--rerank-replicates",
        "3",
        "--rerank-length-penalty-per-1k",
        "0.02",
        "--rerank-max-prompt-chars",
        "4000",
    ])

    assert args.gepa_seed == 19
    assert args.reflection_minibatch_size == 3
    assert args.best_candidate_probability == pytest.approx(0.5)
    assert args.rerank_top_k == 5
    assert args.rerank_replicates == 3
    assert args.rerank_length_penalty_per_1k == pytest.approx(0.02)
    assert args.rerank_max_prompt_chars == 4_000


def test_optimization_cli_accepts_search_only_and_multiple_programs():
    search = parser().parse_args([
        "optimize",
        "--dataset",
        "dataset.jsonl",
        "--prompt",
        "prompt.json",
        "--search-only",
        "--program-output",
        "seed17.json",
    ])
    rerank = parser().parse_args([
        "rerank",
        "--dataset",
        "dataset.jsonl",
        "--prompt",
        "prompt.json",
        "--optimized-program",
        "seed7.json",
        "--optimized-program",
        "seed17.json",
        "--report-output",
        "rerank.json",
    ])

    assert search.search_only is True
    assert search.program_output == Path("seed17.json")
    assert rerank.optimized_program == [Path("seed7.json"), Path("seed17.json")]
    assert rerank.report_output == Path("rerank.json")


def test_repeated_final_gate_evaluates_baseline_with_same_replicate_count(
    tmp_path,
    monkeypatch,
):
    targets = [SymbolTarget("project", "pkg/module.py", "target", "test")]
    reference_rows = [{
        "target": targets[0].__dict__,
        "score": 0.4,
        "coverage": {"valid": True, "num_statements": 1, "num_branches": 0},
    }]
    expected = {
        "results": [{**reference_rows[0], "score": 0.6}],
        "aggregate": {"score": 0.6},
        "run_ids": ["r0", "r1", "r2"],
        "tests_workspaces": ["w0", "w1", "w2"],
    }
    calls = []

    def fake_repeated(
        runner,
        batch_targets,
        bundle,
        candidate_dir,
        **kwargs,
    ):
        calls.append((runner, batch_targets, bundle, candidate_dir, kwargs))
        return expected

    monkeypatch.setattr("src.optimization.cli.evaluate_bundle_repeated", fake_repeated)
    baseline = baseline_bundle()

    result = _repeat_final_baseline(
        "runner",
        targets,
        baseline,
        tmp_path / "candidates",
        split="test",
        replicates=3,
        reference_rows=reference_rows,
    )

    assert result is expected
    assert len(calls) == 1
    assert calls[0][4] == {
        "split": "test",
        "workspace_kind": "baseline",
        "replicates": 3,
        "reference_results": reference_rows,
    }


def test_rerank_selects_stable_candidate_and_keeps_baseline_in_top_k(
    tmp_path,
    monkeypatch,
):
    baseline = baseline_bundle()
    noisy = PromptBundle(
        initial=baseline.initial + " Noisy strategy.", error=baseline.error,
    )
    stable = PromptBundle(
        initial=baseline.initial + " Stable strategy.", error=baseline.error,
    )
    excluded = PromptBundle(
        initial=baseline.initial + " Low ranked strategy.", error=baseline.error,
    )
    target = SymbolTarget("project", "pkg/module.py", "target", "validation")
    scores = {
        bundle_digest(baseline): [0.65, 0.65, 0.65],
        bundle_digest(noisy): [0.90, 0.50, 0.70],
        bundle_digest(stable): [0.70, 0.70, 0.70],
        bundle_digest(excluded): [1.0, 1.0, 1.0],
    }
    calls = []

    def fake_repeated(
        runner,
        targets,
        bundle,
        candidate_dir,
        *,
        split,
        workspace_kind,
        replicates,
        reference_results=None,
    ):
        del runner, candidate_dir, reference_results
        digest = bundle_digest(bundle)
        calls.append((digest, split, workspace_kind, replicates))
        batches = []
        for index, value in enumerate(scores[digest]):
            coverage = {
                "valid": True,
                "covered_statements": int(value * 100),
                "num_statements": 100,
                "covered_branches": 0,
                "num_branches": 0,
            }
            batches.append({
                "results": [{
                    "target": targets[0].__dict__,
                    "score": value,
                    "coverage": coverage,
                    "feedback": "ok",
                }],
                "run_ids": [f"{digest}-r{index}"],
                "tests_workspaces": [f"{digest}-w{index}"],
            })
        return {
            "results": batches[0]["results"],
            "aggregate": aggregate_coverage_score(batches[0]["results"]),
            "batches": batches,
            "run_ids": [value for batch in batches for value in batch["run_ids"]],
            "tests_workspaces": [
                value for batch in batches for value in batch["tests_workspaces"]
            ],
        }

    monkeypatch.setattr(
        "src.optimization.gepa.evaluate_bundle_repeated", fake_repeated,
    )
    result = rerank_prompt_candidates(
        runner=None,
        validation_targets=[target],
        baseline=baseline,
        candidates=[baseline, noisy, stable, excluded],
        validation_scores=[0.10, 0.95, 0.90, 0.20],
        candidate_dir=tmp_path / "candidates",
        top_k=3,
        replicates=3,
    )

    assert result.selected_bundle == stable
    assert result.top_k == 3
    assert [row["digest"] for row in result.leaderboard] == [
        bundle_digest(stable),
        bundle_digest(noisy),
        bundle_digest(baseline),
    ]
    assert result.leaderboard[0]["replicate_scores"] == [0.70, 0.70, 0.70]
    assert result.leaderboard[0]["score_stddev"] == 0.0
    assert bundle_digest(excluded) not in {call[0] for call in calls}


def test_rerank_rejects_locked_test_split():
    baseline = baseline_bundle()
    target = SymbolTarget("project", "pkg/module.py", "target", "test")

    with pytest.raises(ValueError, match="only use the validation split"):
        rerank_prompt_candidates(
            runner=None,
            validation_targets=[target],
            baseline=baseline,
            candidates=[baseline],
            validation_scores=[0.5],
            candidate_dir=Path("candidates"),
            top_k=1,
            replicates=3,
            split="test",
        )


def test_rerank_length_objective_can_select_baseline_or_filter_bloat(
    tmp_path, monkeypatch,
):
    baseline = baseline_bundle()
    long_candidate = PromptBundle(
        initial=baseline.initial + ("x" * 3_000),
        error=baseline.error,
    )
    target = SymbolTarget("project", "pkg/module.py", "target", "validation")
    values = {
        bundle_digest(baseline): 0.70,
        bundle_digest(long_candidate): 0.73,
    }
    calls = []

    def fake_repeated(
        runner,
        targets,
        bundle,
        candidate_dir,
        *,
        split,
        workspace_kind,
        replicates,
        reference_results=None,
    ):
        del runner, candidate_dir, split, workspace_kind, reference_results
        digest = bundle_digest(bundle)
        calls.append(digest)
        coverage = {
            "valid": True,
            "covered_statements": int(values[digest] * 100),
            "num_statements": 100,
            "covered_branches": 0,
            "num_branches": 0,
        }
        row = {
            "target": targets[0].__dict__,
            "coverage": coverage,
            "score": values[digest],
            "feedback": "ok",
        }
        batches = [{"results": [row]} for _ in range(replicates)]
        return {
            "results": [row],
            "aggregate": aggregate_coverage_score([row]),
            "batches": batches,
            "run_ids": [],
            "tests_workspaces": [],
        }

    monkeypatch.setattr(
        "src.optimization.gepa.evaluate_bundle_repeated", fake_repeated,
    )
    penalized = rerank_prompt_candidates(
        runner=None,
        validation_targets=[target],
        baseline=baseline,
        candidates=[baseline, long_candidate],
        validation_scores=[0.70, 0.73],
        candidate_dir=tmp_path / "candidates",
        top_k=2,
        replicates=3,
        length_penalty_per_1k=0.02,
    )

    assert penalized.selected_bundle == baseline
    proposal_row = next(
        row for row in penalized.leaderboard if not row["is_baseline"]
    )
    assert proposal_row["length_penalty"] == pytest.approx(0.06)
    assert proposal_row["selection_score"] == pytest.approx(0.67)

    calls.clear()
    capped = rerank_prompt_candidates(
        runner=None,
        validation_targets=[target],
        baseline=baseline,
        candidates=[baseline, long_candidate],
        validation_scores=[0.70, 0.73],
        candidate_dir=tmp_path / "candidates",
        top_k=2,
        replicates=3,
        max_prompt_chars=len(baseline.initial) + len(baseline.error) + 100,
    )

    assert capped.selected_bundle == baseline
    assert calls == [bundle_digest(baseline)]
    assert capped.filtered_candidates == [{
        "digest": bundle_digest(long_candidate),
        "search_validation_score": 0.73,
        "prompt_chars": len(long_candidate.initial) + len(long_candidate.error),
        "reason": "max_prompt_chars_exceeded",
    }]
    with pytest.raises(ValueError, match="smaller than the baseline"):
        rerank_prompt_candidates(
            runner=None,
            validation_targets=[target],
            baseline=baseline,
            candidates=[baseline],
            validation_scores=[0.70],
            candidate_dir=tmp_path / "candidates",
            top_k=1,
            replicates=3,
            max_prompt_chars=len(baseline.initial) + len(baseline.error) - 1,
        )


def test_rerank_saved_program_pools_candidates_from_multiple_seeds(
    tmp_path, monkeypatch,
):
    from src.optimization import cli

    baseline = baseline_bundle()
    first = PromptBundle(
        initial=baseline.initial + " First seed.", error=baseline.error,
    )
    second = PromptBundle(
        initial=baseline.initial + " Second seed.", error=baseline.error,
    )
    prompt_path = tmp_path / "baseline.json"
    baseline.save(prompt_path)
    programs = []
    configurations = (
        (7, 0.7, first, 0.7),
        (17, 0.5, second, 0.8),
    )
    for seed, best_probability, candidate, score in configurations:
        path = tmp_path / f"seed{seed}.json"
        path.write_text(json.dumps({
            "candidates": [baseline.as_candidate(), candidate.as_candidate()],
            "validation_scores": [0.5, score],
            "optimizer_config": {
                "gepa_seed": seed,
                "reflection_minibatch_size": 3,
                "best_candidate_probability": best_probability,
                "max_metric_calls": 30,
            },
        }), encoding="utf-8")
        programs.append(path)
    artifacts = tmp_path / "artifacts"
    target = SymbolTarget("project", "pkg/module.py", "target", "validation")
    captured = {}

    monkeypatch.setattr(cli, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "load_targets", lambda path, split: [target])
    monkeypatch.setattr(
        cli,
        "_resolve_project_layouts",
        lambda root, targets, sample_repos_dir: {},
    )
    monkeypatch.setattr(
        cli,
        "make_runner",
        lambda args, projects=None: SimpleNamespace(
            config=SimpleNamespace(artifacts_dir=artifacts)
        ),
    )

    def fake_rerank(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            selected_bundle=second,
            leaderboard=[],
            as_dict=lambda: {
                "selected_digest": bundle_digest(second),
                "top_k": 3,
                "replicates": 3,
                "leaderboard": [],
            },
        )

    monkeypatch.setattr(cli, "rerank_prompt_candidates", fake_rerank)
    cli.rerank_saved_program(SimpleNamespace(
        project_root=tmp_path,
        prompt=prompt_path,
        optimized_program=programs,
        dataset=tmp_path / "dataset.jsonl",
        split="validation",
        sample_repos_dir=Path("sample_repo"),
        top_k=5,
        replicates=3,
        output_prompt=None,
    ))

    assert captured["candidates"] == [baseline, first, baseline, second]
    assert captured["validation_scores"] == [0.5, 0.7, 0.5, 0.8]
    report = json.loads(
        (artifacts / "candidate_rerank.json").read_text(encoding="utf-8")
    )
    assert report["gepa_seeds"] == [7, 17]
    assert [
        config["best_candidate_probability"]
        for config in report["optimizer_configs"]
    ] == [0.7, 0.5]
    assert report["source_programs"] == [str(path) for path in programs]
    assert PromptBundle.load(
        artifacts / "prompts" / "gepa_reranked.json"
    ) == second


def test_run_streamed_forwards_retains_and_unbuffers_output(capsys):
    completed = run_streamed(
        [
            sys.executable,
            "-u",
            "-c",
            (
                "import os; "
                "print('unbuffered=' + os.environ['PYTHONUNBUFFERED']); "
                "print('streamed-child-output')"
            ),
        ],
        label="streaming smoke",
    )

    visible = capsys.readouterr().out
    assert completed.returncode == 0
    assert "unbuffered=1" in completed.stdout
    assert "streamed-child-output" in completed.stdout
    assert "[streaming smoke] started" in visible
    assert "streamed-child-output" in visible
    assert "[streaming smoke] finished with exit code 0" in visible


def test_run_streamed_can_capture_without_echoing_child_output(capsys):
    completed = run_streamed(
        [sys.executable, "-u", "-c", "print('captured-only')"],
        label="hidden worker",
        echo=False,
    )

    assert completed.stdout.strip() == "captured-only"
    assert capsys.readouterr().out == ""


def test_reflection_request_log_contains_exact_model_payload(capsys):
    request = {
        "messages": [
            {"role": "system", "content": "system instructions"},
            {"role": "user", "content": "full evidence\nwith newline"},
        ],
        "tools": [{"type": "function", "function": {"name": "update"}}],
        "tool_choice": {"type": "function", "function": {"name": "update"}},
    }

    log_reflection_request(request)

    output = capsys.readouterr().out
    assert output.startswith("PROMPTOPT_REFLECTION_REQUEST_BEGIN\n")
    assert output.endswith("PROMPTOPT_REFLECTION_REQUEST_END\n")
    payload = output.removeprefix(
        "PROMPTOPT_REFLECTION_REQUEST_BEGIN\n"
    ).removesuffix("PROMPTOPT_REFLECTION_REQUEST_END\n")
    assert json.loads(payload) == request


def test_run_coverage_does_not_mask_real_pytest_failures(tmp_path, monkeypatch):
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
            args=command, returncode=1, stdout="test failed", stderr=None
        )

    monkeypatch.setattr("src.optimization.coveragepy.run_streamed", fake_run)
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
    assert completed.stdout == "test failed"
    assert len(calls) == 2
    assert (tmp_path / "coverage.json").is_file()


def test_runner_keeps_denominators_but_scores_failing_suite_as_zero(
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
        "src.optimization.runner.run_streamed",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="coverup ok"),
    )

    def fake_run_coverage(**kwargs):
        kwargs["output"].write_text(json.dumps({
            "files": {
                "pkg/module.py": {
                    "functions": {
                        "target": {
                            "executed_lines": [1, 2],
                            "missing_lines": [3],
                            "executed_branches": [[1, 2]],
                            "missing_branches": [[1, 3]],
                            "summary": {
                                "covered_lines": 2,
                                "num_statements": 3,
                                "covered_branches": 1,
                                "num_branches": 2,
                            },
                        }
                    }
                }
            }
        }), encoding="utf-8")
        return SimpleNamespace(returncode=1, stdout="2 failed, 23 passed")

    monkeypatch.setattr("src.optimization.runner.run_coverage", fake_run_coverage)
    runner = CoverUpExperimentRunner(ExperimentConfig(
        project_root=tmp_path,
        package_dir=package_dir,
        tests_dir=tests_dir,
        artifacts_dir=artifacts_dir,
        coverup_model="fake-model",
    ))

    record = runner.evaluate_batch(
        [SymbolTarget("project", "pkg/module.py", "target", "train")],
        prompt_path,
        candidate_id="failing-suite",
        split="train",
    )

    score = record.results[0].score
    assert score["score"] == 0.0
    assert score["covered_statements"] == 0
    assert score["num_statements"] == 3
    assert score["covered_branches"] == 0
    assert score["num_branches"] == 2
    assert score["valid"] is True
    assert score["tests_passed"] is False
    assert score["pytest_exit_code"] == 1
    assert "2 failed, 23 passed" in record.results[0].feedback


def test_runner_rejects_explicit_target_discovery_failure(tmp_path, monkeypatch):
    package_dir = tmp_path / "sample_repo" / "pkg"
    tests_dir = tmp_path / "sample_repo" / "tests"
    artifacts_dir = tmp_path / "artifacts"
    package_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)
    prompt_path = tmp_path / "prompt.json"
    baseline_bundle().save(prompt_path)

    def fake_subprocess_run(command, **kwargs):
        spec = json.loads(
            Path(command[command.index("--target-spec-file") + 1]).read_text(
                encoding="utf-8"
            )
        )[0]
        Path(command[command.index("--trace-file") + 1]).write_text(
            json.dumps({
                "source_file": spec["source_file"],
                "symbol": spec["symbol"],
                "name": "target",
                "outcome": "target_discovery_failed",
            }) + "\n",
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stdout="no matching segment")

    def fake_run_coverage(**kwargs):
        kwargs["output"].write_text(json.dumps({
            "files": {
                "pkg/module.py": {
                    "functions": {
                        "Small.target": {
                            "executed_lines": [],
                            "missing_lines": [3],
                            "executed_branches": [],
                            "missing_branches": [],
                            "summary": {
                                "covered_lines": 0,
                                "num_statements": 1,
                                "covered_branches": 0,
                                "num_branches": 0,
                            },
                        }
                    }
                }
            }
        }), encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="coverage ok")

    monkeypatch.setattr("src.optimization.runner.run_streamed", fake_subprocess_run)
    monkeypatch.setattr("src.optimization.runner.run_coverage", fake_run_coverage)
    runner = CoverUpExperimentRunner(ExperimentConfig(
        project_root=tmp_path,
        package_dir=package_dir,
        tests_dir=tests_dir,
        artifacts_dir=artifacts_dir,
        coverup_model="fake-model",
    ))

    result = runner.evaluate_batch(
        [SymbolTarget("project", "pkg/module.py", "Small.target", "train")],
        prompt_path,
        candidate_id="discovery-failure",
        split="train",
    ).results[0]

    assert result.score["valid"] is False
    assert result.attempt_traces[0]["outcome"] == "target_discovery_failed"
    assert "Target discovery failed" in result.feedback


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
    target_specs = []

    def fake_subprocess_run(command, **kwargs):
        commands.append(command)
        specs = json.loads(
            Path(command[command.index("--target-spec-file") + 1]).read_text(
                encoding="utf-8"
            )
        )
        target_specs.append(specs)
        spec = specs[0]
        trace_path = Path(command[command.index("--trace-file") + 1])
        trace_path.write_text(
            json.dumps({
                "source_file": spec["source_file"],
                "symbol": spec["symbol"],
                "name": spec["symbol"],
                "component": "initial",
                "outcome": "coverage_gain_saved",
            }) + "\n",
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stdout="coverup ok")

    def fake_run_coverage(**kwargs):
        return SimpleNamespace(returncode=1, stdout="no generated tests")

    monkeypatch.setattr("src.optimization.runner.run_streamed", fake_subprocess_run)
    monkeypatch.setattr("src.optimization.runner.run_coverage", fake_run_coverage)
    runner = CoverUpExperimentRunner(ExperimentConfig(
        project_root=tmp_path,
        package_dir=package_dir,
        tests_dir=tests_dir,
        artifacts_dir=artifacts_dir,
        coverup_model="fake-model",
        target_context=True,
        repository_test_context=True,
        failure_context=True,
        failure_context_max_chars=3_500,
        salvage_failing_tests=True,
        salvage_max_prunes=5,
    ))
    targets = [
        SymbolTarget("project", "pkg/a.py", "first", "train"),
        # Deliberately repeat the qualname in another file. Exact target specs and
        # per-target workspaces must prevent filename/counter races.
        SymbolTarget("project", "pkg/b.py", "first", "train"),
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

    assert len(commands) == 4
    assert {
        command[command.index("--target-symbols") + 1] for command in commands
    } == {"first"}
    assert all(len(spec) == 1 for spec in target_specs)
    assert {spec[0]["source_file"] for spec in target_specs} == {
        "pkg/a.py", "pkg/b.py",
    }
    assert len({
        command[command.index("--tests-dir") + 1] for command in commands
    }) == 4
    assert all(
        command[command.index("--max-concurrency") + 1] == "1"
        for command in commands
    )
    assert all("--trace-file" in command for command in commands)
    assert all("--target-context" in command for command in commands)
    assert all(
        Path(command[command.index("--context-tests-dir") + 1])
        == tests_dir.resolve()
        for command in commands
    )
    assert all(
        command[command.index("--target-context-max-chars") + 1] == "6000"
        for command in commands
    )
    assert all("--failure-context" in command for command in commands)
    assert all(
        command[command.index("--failure-context-max-chars") + 1] == "3500"
        for command in commands
    )
    assert all(
        Path(command[command.index("--failure-context-root") + 1])
        == package_dir.parent.resolve()
        for command in commands
    )
    assert all("--salvage-failing-tests" in command for command in commands)
    assert all(
        command[command.index("--salvage-max-prunes") + 1] == "5"
        for command in commands
    )
    assert all("--no-final-coverage" in command for command in commands)
    assert Path(record.tests_workspace) == stale_empty_workspace.resolve()
    assert Path(baseline_record.tests_workspace) == (
        artifacts_dir / "generated_tests" / "train" / "tests_base_line_baseline"
    ).resolve()
    assert Path(record.tests_workspace).is_dir()
    assert len(record.results) == 2
    assert record.results[0].attempt_traces[0]["component"] == "initial"
    assert record.results[1].attempt_traces[0]["component"] == "initial"


@pytest.mark.parametrize("split", ["train", "validation", "test"])
def test_runner_batches_generation_but_scores_and_reports_each_target_separately(
    tmp_path, monkeypatch, split,
):
    package_dir = tmp_path / "sample_repo" / "pkg"
    tests_dir = tmp_path / "sample_repo" / "tests"
    artifacts_dir = tmp_path / "artifacts"
    package_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)
    prompt_path = tmp_path / "prompt.json"
    baseline_bundle().save(prompt_path)
    coverup_commands = []
    coverage_test_paths = []
    coverage_basetemps = []
    generation_barrier = threading.Barrier(2)
    coverage_barrier = threading.Barrier(2)

    def fake_subprocess_run(command, **kwargs):
        coverup_commands.append(command)
        workspace = Path(command[command.index("--tests-dir") + 1])
        spec = json.loads(Path(
            command[command.index("--target-spec-file") + 1]
        ).read_text(encoding="utf-8"))[0]
        generated_test = f"def test_{spec['symbol']}(): pass"
        test_path = workspace / "test_opt_1.py"
        test_path.write_text(generated_test + "\n", encoding="utf-8")
        trace_path = Path(command[command.index("--trace-file") + 1])
        trace_path.write_text(
            json.dumps({
                "source_file": spec["source_file"],
                "symbol": spec["symbol"],
                "name": spec["symbol"],
                "component": "initial",
                "outcome": "coverage_gain_saved",
                "generated_test": generated_test,
                "saved_test": str(test_path),
            }) + "\n",
            encoding="utf-8",
        )
        # Proves target generation itself is concurrent, not merely coverage.
        generation_barrier.wait(timeout=2)
        return SimpleNamespace(returncode=0, stdout="coverup ok")

    def fake_run_coverage(**kwargs):
        selected = [Path(path) for path in kwargs["test_paths"]]
        coverage_test_paths.append(selected)
        coverage_basetemps.append(Path(kwargs["pytest_basetemp"]))
        assert len(selected) == 1
        # A serial implementation times out here; both target coverage workers
        # must enter before either is allowed to produce its report.
        coverage_barrier.wait(timeout=2)
        first = "test_first" in selected[0].read_text(encoding="utf-8")
        source_file = "pkg/a.py" if first else "pkg/b.py"
        symbol = "first" if first else "second"
        executed = [1] if first else []
        missing = [] if first else [1]
        kwargs["output"].write_text(json.dumps({
            "files": {
                source_file: {
                    "functions": {
                        symbol: {
                            "executed_lines": executed,
                            "missing_lines": missing,
                            "executed_branches": [],
                            "missing_branches": [],
                            "summary": {
                                "covered_lines": len(executed),
                                "num_statements": 1,
                                "covered_branches": 0,
                                "num_branches": 0,
                            },
                        }
                    }
                }
            }
        }), encoding="utf-8")
        return SimpleNamespace(
            returncode=0 if first else 1,
            stdout="first passed" if first else "second-target failure",
        )

    monkeypatch.setattr("src.optimization.runner.run_streamed", fake_subprocess_run)
    monkeypatch.setattr("src.optimization.runner.run_coverage", fake_run_coverage)
    runner = CoverUpExperimentRunner(ExperimentConfig(
        project_root=tmp_path,
        package_dir=package_dir,
        tests_dir=tests_dir,
        artifacts_dir=artifacts_dir,
        coverup_model="fake-model",
        max_concurrency=2,
    ))
    targets = [
        SymbolTarget("project", "pkg/a.py", "first", split),
        SymbolTarget("project", "pkg/b.py", "second", split),
    ]

    record = runner.evaluate_batch(
        targets, prompt_path, candidate_id="candidate", split=split,
    )

    assert len(coverup_commands) == 2
    assert {
        command[command.index("--target-symbols") + 1]
        for command in coverup_commands
    } == {"first", "second"}
    assert all(
        command[command.index("--max-concurrency") + 1] == "1"
        for command in coverup_commands
    )
    assert all("--no-final-coverage" in command for command in coverup_commands)
    assert len(coverage_test_paths) == 2
    assert len({paths[0].name for paths in coverage_test_paths}) == 2
    assert len(set(coverage_basetemps)) == 2
    assert len({path.parent for path in coverage_basetemps}) == 1
    assert coverage_basetemps[0].parent.name == "pytest_tmp"
    generated_root = artifacts_dir / "generated_tests" / split
    assert len(list(generated_root.iterdir())) == 1
    persistent_workspace = Path(record.tests_workspace)
    assert len(list(persistent_workspace.glob("test_opt_*.py"))) == 2
    for result in record.results:
        saved_test = Path(result.attempt_traces[0]["saved_test"])
        assert saved_test.parent == persistent_workspace
        assert saved_test.is_file()
    run_dir = artifacts_dir / "runs" / "candidate" / split / record.run_id
    assert [path.name for path in run_dir.iterdir()] == ["record.json"]
    first_result, second_result = record.results
    assert first_result.score["score"] == 1.0
    assert first_result.attempt_traces[0]["generated_test"].startswith("def test_first")
    assert "second-target failure" not in first_result.feedback
    assert second_result.score["score"] == 0.0
    assert second_result.score["tests_passed"] is False
    assert second_result.attempt_traces[0]["generated_test"].startswith("def test_second")
    assert "second-target failure" in second_result.feedback


def test_local_smoke_gepa_receives_each_subsample_trace_from_one_batch_workspace(
    tmp_path, monkeypatch,
):
    package_dir = tmp_path / "sample_repo" / "pkg"
    package_dir.mkdir(parents=True)
    (package_dir / "a.py").write_text(
        "def first(value):\n    return value + 1\n", encoding="utf-8"
    )
    (package_dir / "b.py").write_text(
        "def second(value):\n    if value:\n        return 1\n    return 0\n",
        encoding="utf-8",
    )
    artifacts_dir = tmp_path / "artifacts"
    coverup_commands = []

    def fake_subprocess_run(command, **kwargs):
        coverup_commands.append(command)
        workspace = Path(command[command.index("--tests-dir") + 1])
        spec = json.loads(Path(
            command[command.index("--target-spec-file") + 1]
        ).read_text(encoding="utf-8"))[0]
        test_path = workspace / "test_opt_1.py"
        generated_test = f"def test_{spec['symbol']}(): pass"
        test_path.write_text(generated_test + "\n", encoding="utf-8")
        trace = {
            "source_file": spec["source_file"],
            "symbol": spec["symbol"],
            "name": spec["symbol"],
            "component": "initial",
            "outcome": "coverage_gain_saved",
            "generated_test": generated_test,
            "saved_test": str(test_path),
        }
        Path(command[command.index("--trace-file") + 1]).write_text(
            json.dumps(trace) + "\n",
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stdout="local generator ok")

    def fake_run_coverage(**kwargs):
        assert len(kwargs["test_paths"]) == 1
        generated_test = Path(kwargs["test_paths"][0]).read_text(encoding="utf-8")
        is_first = "test_first" in generated_test
        spec = {
            "source_file": "pkg/a.py" if is_first else "pkg/b.py",
            "symbol": "first" if is_first else "second",
        }
        kwargs["output"].write_text(json.dumps({
            "files": {
                spec["source_file"]: {
                    "functions": {
                        spec["symbol"]: {
                            "executed_lines": [1] if is_first else [1, 2],
                            "missing_lines": [] if is_first else [3, 4],
                            "executed_branches": [],
                            "missing_branches": [] if is_first else [[2, 4]],
                            "summary": {
                                "covered_lines": 1 if is_first else 2,
                                "num_statements": 1 if is_first else 4,
                                "covered_branches": 0,
                                "num_branches": 0 if is_first else 1,
                            },
                        }
                    }
                }
            }
        }), encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout=f"{spec['symbol']} passed")

    monkeypatch.setattr("src.optimization.runner.run_streamed", fake_subprocess_run)
    monkeypatch.setattr("src.optimization.runner.run_coverage", fake_run_coverage)
    runner = CoverUpExperimentRunner(ExperimentConfig(
        project_root=tmp_path,
        package_dir=package_dir,
        tests_dir=tmp_path / "sample_repo" / "tests",
        artifacts_dir=artifacts_dir,
        coverup_model="local-fake-model",
        max_concurrency=2,
    ))
    targets = [
        SymbolTarget("project", "pkg/a.py", "first", "train"),
        SymbolTarget("project", "pkg/b.py", "second", "train"),
    ]
    baseline = baseline_bundle()
    adapter = CoverUpPromptAdapter(
        runner=runner,
        candidate_dir=artifacts_dir / "candidates",
        targets_by_split={"train": targets},
        baseline=baseline,
        reflection_lm=lambda prompt: ["<template>unchanged</template>"],
    )

    evaluated = adapter.evaluate(
        targets, baseline.as_candidate(), capture_traces=True,
    )
    reflective = adapter.make_reflective_dataset(
        baseline.as_candidate(), evaluated, ["initial"],
    )["initial"]

    assert len(coverup_commands) == 2
    assert {
        command[command.index("--target-symbols") + 1]
        for command in coverup_commands
    } == {"first", "second"}
    assert len(list((artifacts_dir / "generated_tests" / "train").iterdir())) == 1
    assert [output["target"]["symbol"] for output in evaluated.outputs] == [
        "first", "second",
    ]
    rows_by_target = {row["Inputs"]["target"]: row for row in reflective}
    assert set(rows_by_target) == {"pkg/a.py::first", "pkg/b.py::second"}
    assert rows_by_target["pkg/a.py::first"]["Generated Outputs"][
        "candidate_test"
    ] == "def test_first(): pass"
    assert rows_by_target["pkg/b.py::second"]["Generated Outputs"][
        "candidate_test"
    ] == "def test_second(): pass"
    assert "Remaining lines: [3, 4]" in rows_by_target[
        "pkg/b.py::second"
    ]["Feedback"]


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
        "src.optimization.runner.run_streamed",
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
        "src.optimization.runner.run_streamed",
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


def test_score_symbol_weights_branch_at_seventy_percent():
    before = coverage(
        missing_lines=(1, 2),
        missing_branches=((1, 2), (1, 3)),
    )
    after = coverage(
        executed_lines=(1,),
        executed_branches=((1, 2), (1, 3)),
    )

    result = score_symbol(before, after)

    assert result.statement_gain == 0.5
    assert result.branch_gain == 1.0
    assert result.score == pytest.approx(0.85)


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


def test_aggregate_score_weights_branch_at_seventy_percent():
    aggregate = aggregate_coverage_score([{
        "coverage": {
            "valid": True,
            "covered_statements": 10,
            "num_statements": 10,
            "covered_branches": 0,
            "num_branches": 10,
        }
    }])

    assert aggregate["statement_coverage"] == 1.0
    assert aggregate["branch_coverage"] == 0.0
    assert aggregate["score"] == pytest.approx(0.3)


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


def test_metric_batches_targets_once_and_serializes_batch_cache(tmp_path):
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
    assert runner.max_active == 1
    assert runner.calls == 1


def test_batch_evaluation_deduplicates_repeated_minibatch_targets(tmp_path):
    class DuplicateDetectingRunner:
        def __init__(self):
            self.config = SimpleNamespace(max_concurrency=2, rate_limit=None)
            self.candidate_ids = []

        def evaluate_batch(
            self, targets, candidate, *, candidate_id=None, split=None,
            workspace_kind="candidate",
        ):
            self.candidate_ids.append(candidate_id)
            return SimpleNamespace(
                run_id="run-once",
                tests_workspace="tests-candidate",
                results=[SimpleNamespace(
                    target=targets[0],
                    score={"score": 0.5},
                    feedback="ok",
                )],
            )

    runner = DuplicateDetectingRunner()
    target = SymbolTarget("project", "pkg/a.py", "first")

    result = evaluate_bundle_batch_cached(
        runner,
        [target, target],
        baseline_bundle(),
        tmp_path,
        split="train",
    )

    assert len(runner.candidate_ids) == 1
    assert len(result["results"]) == 1
    assert result["results"][0]["target"] == target.__dict__


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
    assert len(runner.calls) == 2
    assert len(set(runner.calls)) == 2
    assert all(call.startswith(bundle_digest(baseline) + "-") for call in runner.calls)
    assert sum(call.endswith("-r1") for call in runner.calls) == 1
    assert "pkg/a.py::first" == reflective["initial"][0]["Inputs"]["target"]
    assert "def first" in reflective["initial"][0]["Inputs"]["source_context"]
    assert (
        reflective["initial"][0]["Generated Outputs"]["execution_episodes"][0]
        ["initial_attempts"][0]
        ["generated_test"]
        == "def test_first(): pass"
    )


def test_direct_gepa_adapter_evaluates_only_requested_minibatch(tmp_path):
    targets = [
        SymbolTarget("project", "pkg/a.py", "first", "train"),
        SymbolTarget("project", "pkg/b.py", "second", "train"),
    ]
    baseline = baseline_bundle()
    adapter = CoverUpPromptAdapter(
        runner=SimpleNamespace(),
        candidate_dir=tmp_path / "candidates",
        targets_by_split={"train": targets},
        baseline=baseline,
        reflection_lm=lambda prompt: ["<template>unchanged</template>"],
    )
    evaluated_target_batches = []

    def fake_evaluate_replicates(requested, bundle, *, split):
        evaluated_target_batches.append(list(requested))
        return [{
            "results": [{
                "target": target.__dict__,
                "score": 0.5,
                "coverage": {
                    "valid": True,
                    "covered_statements": 1,
                    "num_statements": 2,
                    "covered_branches": 0,
                    "num_branches": 0,
                    "statement_gain": 0.5,
                    "branch_gain": 1.0,
                },
                "feedback": "ok",
                "attempt_traces": [],
            } for target in requested],
        }]

    adapter._evaluate_replicates = fake_evaluate_replicates
    evaluated = adapter.evaluate(
        [targets[1]], baseline.as_candidate(), capture_traces=False
    )

    assert evaluated_target_batches == [[targets[1]]]
    assert [output["target"]["symbol"] for output in evaluated.outputs] == ["second"]


def test_reflection_compares_candidate_with_parent_and_balances_exemplars(tmp_path):
    project = tmp_path / "sample_repo"
    package = project / "pkg"
    package.mkdir(parents=True)
    (package / "a.py").write_text(
        "def improved_target(value):\n    return value + 1\n",
        encoding="utf-8",
    )
    (package / "b.py").write_text(
        "def regressed_target(value):\n    return value - 1\n",
        encoding="utf-8",
    )

    class FakeRunner:
        def __init__(self):
            self.config = SimpleNamespace(
                package_dir=package,
                project_root=tmp_path,
            )

        def evaluate_batch(
            self, targets, prompt_template, *, candidate_id=None, split=None,
            workspace_kind="candidate",
        ):
            prompt = json.loads(Path(prompt_template).read_text(encoding="utf-8"))
            if "Contrastive marker" in prompt["initial"]:
                version = "candidate"
            elif "Parent marker" in prompt["initial"]:
                version = "parent"
            else:
                version = "baseline"
            scores = {
                "improved_target": {
                    "candidate": 0.8, "parent": 0.6, "baseline": 0.4,
                },
                "regressed_target": {
                    "candidate": 0.2, "parent": 0.8, "baseline": 0.9,
                },
            }
            results = []
            for target in targets:
                value = scores[target.symbol][version]
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
                        "remaining_branches": [],
                        "valid": True,
                    },
                    feedback=f"feedback for {version} {target.symbol}",
                    attempt_traces=[{
                        "attempt": 1,
                        "component": "initial",
                        "outcome": "coverage_gain_saved",
                        "generated_test": f"def test_{version}_{target.symbol}(): pass",
                    }],
                ))
            return SimpleNamespace(
                run_id=f"run-{candidate_id}",
                tests_workspace=f"tests-{candidate_id}",
                results=results,
            )

    baseline = baseline_bundle()
    parent_initial = baseline.initial.replace(
        "Create new pytest test functions",
        "Parent marker: preserve verified behavior.\n"
        "Create new pytest test functions",
    )
    proposed_initial = parent_initial.replace(
        "Parent marker: preserve verified behavior.",
        "Parent marker: preserve verified behavior.\n"
        "Contrastive marker: compare causal outcomes.",
    )
    proposed_templates = iter((parent_initial, proposed_initial))

    def reflection_lm(**kwargs):
        return tool_call_response(
            "initial",
            {"initial": next(proposed_templates)},
            diagnosis="one instruction changes generated behavior",
            evidence=["candidate and parent have different outcomes"],
        )

    adapter = CoverUpPromptAdapter(
        runner=FakeRunner(),
        candidate_dir=tmp_path / "candidates",
        targets_by_split={},
        baseline=baseline,
        reflection_lm=reflection_lm,
    )
    parent_updates = adapter.propose_new_texts(
        baseline.as_candidate(),
        {"initial": [{"Feedback": "add one evidence-backed instruction"}]},
        ["initial"],
    )
    parent = {**baseline.as_candidate(), **parent_updates}
    candidate_updates = adapter.propose_new_texts(
        parent,
        {"initial": [{"Feedback": "compare the candidate with its direct parent"}]},
        ["initial"],
    )
    candidate = {**parent, **candidate_updates}
    targets = [
        SymbolTarget("project", "pkg/a.py", "improved_target", "train"),
        SymbolTarget("project", "pkg/b.py", "regressed_target", "train"),
    ]
    adapter.targets_by_split = {"train": targets}

    evaluated = adapter.evaluate(targets, candidate, capture_traces=True)
    reflective = adapter.make_reflective_dataset(
        candidate, evaluated, ["initial"]
    )["initial"]
    by_target = {row["Inputs"]["target"]: row for row in reflective}
    improved = by_target["pkg/a.py::improved_target"]
    regressed = by_target["pkg/b.py::regressed_target"]

    improved_output = improved["Generated Outputs"]
    assert improved_output["candidate_score"] == pytest.approx(0.8)
    assert improved_output["parent_score"] == pytest.approx(0.6)
    assert improved_output["baseline_score"] == pytest.approx(0.4)
    assert improved_output["score_delta"] == pytest.approx(0.2)
    assert improved_output["baseline_score_delta"] == pytest.approx(0.4)
    assert improved_output["comparison_outcome"] == "improved"
    assert improved_output["exemplar_type"] == "positive"
    assert "test_candidate_improved_target" in improved_output["candidate_test"]
    assert "test_parent_improved_target" in improved_output["parent_test"]
    assert "baseline_test" not in improved_output
    assert improved["Inputs"]["changed_components"] == ["initial"]

    regressed_output = regressed["Generated Outputs"]
    assert regressed_output["candidate_score"] == pytest.approx(0.2)
    assert regressed_output["parent_score"] == pytest.approx(0.8)
    assert regressed_output["baseline_score"] == pytest.approx(0.9)
    assert regressed_output["score_delta"] == pytest.approx(-0.6)
    assert regressed_output["baseline_score_delta"] == pytest.approx(-0.7)
    assert regressed_output["comparison_outcome"] == "regressed"
    assert regressed_output["exemplar_type"] == "regression"
    assert "test_candidate_regressed_target" in regressed_output["candidate_test"]
    assert "test_parent_regressed_target" in regressed_output["parent_test"]
    assert "candidate regressed versus parent" in regressed["Feedback"]

    assert [
        row["Generated Outputs"]["exemplar_type"] for row in reflective[:2]
    ] == ["regression", "positive"]
    trace_path = tmp_path / "candidates" / "reflection_traces.jsonl"
    trace = json.loads(trace_path.read_text(encoding="utf-8").splitlines()[-1])
    assert trace["schema_version"] == 3
    assert trace["candidate_digest"] == bundle_digest(
        PromptBundle.from_candidate(candidate)
    )
    assert trace["components_to_update"] == ["initial"]
    assert [
        row["Generated Outputs"]["exemplar_type"]
        for row in trace["records"]["initial"][:2]
    ] == ["regression", "positive"]


def test_reflection_uses_only_trajectories_that_exercised_component(tmp_path):
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


def test_reflection_reconstructs_initial_error_repair_episode(tmp_path):
    baseline = baseline_bundle()
    adapter = CoverUpPromptAdapter(
        runner=SimpleNamespace(),
        candidate_dir=tmp_path,
        targets_by_split={},
        baseline=baseline,
        reflection_lm=lambda prompt: ["<template>unused</template>"],
    )
    evaluation = SimpleNamespace(trajectories=[{
        "target": {"source_file": "pkg/a.py", "symbol": "first"},
        "score": 0.5,
        "replicate_scores": [0.5],
        "feedback": "one branch remains",
        "source_context": "def first(value): ...",
        "attempt_traces": [
            {
                "attempt": 1,
                "replicate": 0,
                "component": "initial",
                "outcome": "test_error",
                "generated_test": "def test_initial(): assert broken",
                "execution_error": "NameError: broken",
                "next_component": "error",
            },
            {
                "attempt": 2,
                "replicate": 0,
                "component": "error",
                "outcome": "test_error",
                "prompt_input": "Repair NameError: broken",
                "generated_test": "def test_repair_one(): assert still_broken",
                "execution_error": "NameError: still_broken",
                "next_component": "error",
            },
            {
                "attempt": 3,
                "replicate": 0,
                "component": "error",
                "outcome": "coverage_gain_saved",
                "prompt_input": "Repair NameError: still_broken",
                "generated_test": "def test_repair_two(): assert True",
                "gained_lines": [2],
                "gained_branches": [[2, 3]],
                "remaining_lines": [],
                "remaining_branches": [],
            },
        ],
    }])

    row = adapter.make_reflective_dataset(
        baseline.as_candidate(), evaluation, ["error"]
    )["error"][0]
    output = row["Generated Outputs"]
    episode = output["execution_episodes"][0]

    assert "baseline_test" not in output
    assert episode["initial_attempts"][0]["generated_test"].startswith(
        "def test_initial"
    )
    assert len(episode["repair_transitions"]) == 2
    first, second = episode["repair_transitions"]
    assert first["failing_test"].startswith("def test_initial")
    assert first["error"] == "NameError: broken"
    assert first["repaired_test"].startswith("def test_repair_one")
    assert first["execution_error_after"] == "NameError: still_broken"
    assert first["failure_before"] == {
        "failure_stage": "execution",
        "failure_type": "name_error",
        "error_type": "NameError",
        "error_message": "broken",
    }
    assert first["failure_after"] == {
        "failure_stage": "execution",
        "failure_type": "name_error",
        "error_type": "NameError",
        "error_message": "still_broken",
    }
    assert second["failing_test"].startswith("def test_repair_one")
    assert second["error"] == "NameError: still_broken"
    assert second["repaired_test"].startswith("def test_repair_two")
    assert second["outcome"] == "coverage_gain_saved"
    assert episode["terminal_failure"] == {}


def test_failure_taxonomy_extracts_assertion_and_generated_test_frame():
    failure = classify_attempt_failure({
        "outcome": "test_error",
        "execution_error": (
            "FAILED tests/test_generated.py::test_value - AssertionError\n"
            "tests/test_generated.py:42: in test_value\n"
            "E   assert 'raw' == 'normalized'\n"
            "E   AssertionError: expected normalized value"
        ),
    })

    assert failure == {
        "failure_stage": "assertion",
        "failure_type": "assertion_error",
        "error_type": "AssertionError",
        "error_message": "expected normalized value",
        "actual": "'raw'",
        "expected": "'normalized'",
        "comparison": "==",
        "actionable_frame": {
            "path": "tests/test_generated.py",
            "line": 42,
            "function": "test_value",
        },
    }


def test_failure_taxonomy_distinguishes_import_coverage_and_exhausted_repair():
    import_failure = classify_attempt_failure({
        "outcome": "test_error",
        "execution_error": (
            "tmp_test_generated.py:7: in <module>\n"
            "E   ModuleNotFoundError: No module named 'optional_dep'"
        ),
    })
    partial = classify_attempt_failure({
        "outcome": "coverage_gain_saved",
        "remaining_lines": [10],
        "remaining_branches": [[10, 12]],
    })
    exhausted = classify_attempt_failure(
        {"outcome": "max_attempts_exhausted"},
        {
            "outcome": "test_error",
            "execution_error": "E   TypeError: unexpected keyword argument 'mode'",
        },
    )

    assert import_failure["failure_stage"] == "collection"
    assert import_failure["failure_type"] == "import_error"
    assert partial == {
        "failure_stage": "coverage",
        "failure_type": "partial_coverage",
    }
    assert exhausted == {
        "failure_stage": "repair",
        "failure_type": "max_attempts_exhausted",
        "root_failure_stage": "execution",
        "root_failure_type": "type_error",
        "error_type": "TypeError",
        "error_message": "unexpected keyword argument 'mode'",
    }


def test_causal_component_selector_prefers_terminal_error_failures():
    selector = CausalReflectionComponentSelector()
    candidate = baseline_bundle().as_candidate()
    trajectories = [{
        "score": 0.2,
        "attempt_traces": [
            {
                "attempt": 1,
                "component": "initial",
                "outcome": "test_error",
            },
            {
                "attempt": 2,
                "component": "error",
                "outcome": "test_error",
            },
            {
                "attempt": 3,
                "component": "error",
                "outcome": "no_coverage_gain_unrepairable",
            },
        ],
    }]

    selected = selector(None, trajectories, [0.2], 0, candidate)

    assert selected == ["error"]


def test_causal_component_selector_never_selects_unexercised_error():
    selector = CausalReflectionComponentSelector()
    candidate = baseline_bundle().as_candidate()
    trajectories = [{
        "score": 0.1,
        "attempt_traces": [{
            "attempt": 1,
            "component": "initial",
            "outcome": "no_coverage_gain_unrepairable",
        }],
    }]

    selected = selector(None, trajectories, [0.1], 0, candidate)

    assert selected == ["initial"]


def test_causal_component_selector_returns_noop_without_failure_evidence():
    selector = CausalReflectionComponentSelector()
    candidate = baseline_bundle().as_candidate()
    trajectories = [{
        "score": 1.0,
        "attempt_traces": [{
            "attempt": 1,
            "component": "initial",
            "outcome": "coverage_gain_saved",
            "gained_lines": [1],
            "remaining_lines": [],
            "gained_branches": [],
            "remaining_branches": [],
        }],
    }]

    selected = selector(None, trajectories, [1.0], 0, candidate)

    assert selected == []


def test_llm_component_selector_always_exposes_both_after_any_failure():
    selector = LLMReflectionComponentSelector()
    candidate = baseline_bundle().as_candidate()
    trajectories = [{
        "score": 0.1,
        "attempt_traces": [
            {"component": "initial", "outcome": "test_error"},
        ],
    }]

    selected = selector(None, trajectories, [0.1], 0, candidate)

    assert selected == ["initial", "error"]


def test_component_update_parser_accepts_native_tool_call_objects_only():
    response = tool_call_response(
        "initial",
        {"initial": baseline_bundle().initial},
        diagnosis="preserve reachability constraints",
        evidence=["the initial attempt missed a branch"],
    )
    arguments = json.loads(response[0]["tool_calls"][0]["function"]["arguments"])
    native_response = [{
        "text": None,
        "tool_calls": [SimpleNamespace(function=SimpleNamespace(
            name="update_prompt_component",
            arguments=json.dumps(arguments),
        ))],
    }]

    parsed = CoverUpPromptAdapter._extract_component_update(native_response)

    assert parsed == arguments
    assert CoverUpPromptAdapter._extract_component_update(
        [json.dumps(arguments)]
    ) is None


def test_component_update_parser_rejects_missing_strategy_contract():
    incomplete = {
        "component": "initial",
        "replacements": {"initial": baseline_bundle().initial},
        "diagnosis": "a narrow patch without a reusable strategy",
        "evidence": ["one branch was missed"],
    }
    response = [{
        "text": None,
        "tool_calls": [{
            "function": {
                "name": "update_prompt_component",
                "arguments": json.dumps(incomplete),
            },
        }],
    }]

    assert CoverUpPromptAdapter._extract_component_update(response) is None


def test_prompt_mutation_can_update_all_components_in_one_call(tmp_path):
    baseline = baseline_bundle()
    improved_initial = baseline.initial.replace(
        "Create new pytest test functions",
        "Analyze reachability first.\nCreate new pytest test functions",
    )
    improved_error = "Coordinate repair with initial constraints.\n" + baseline.error
    calls = []

    def reflection_lm(**kwargs):
        calls.append(kwargs)
        return tool_call_response(
            "all",
            {"initial": improved_initial, "error": improved_error},
            diagnosis="generation and repair use inconsistent constraints",
            evidence=["both stages have terminal failures"],
        )

    adapter = CoverUpPromptAdapter(
        runner=SimpleNamespace(),
        candidate_dir=tmp_path,
        targets_by_split={},
        baseline=baseline,
        reflection_lm=reflection_lm,
    )
    proposals = adapter.propose_new_texts(
        baseline.as_candidate(),
        {
            "initial": [{"Feedback": "initial failed"}],
            "error": [],
        },
        ["initial", "error"],
    )

    assert proposals["initial"].startswith(improved_initial)
    assert proposals["error"].startswith(improved_error)
    assert STRATEGY_PLAYBOOK_BEGIN in proposals["initial"]
    assert STRATEGY_PLAYBOOK_END in proposals["error"]
    assert len(calls) == 1
    decision = json.loads(
        (tmp_path / "reflection_decisions.jsonl").read_text(encoding="utf-8")
    )
    assert decision["one_call"] is True
    assert decision["selection"] == "all"
    assert decision["changed_components"] == ["initial", "error"]
    assert decision["status"] == "accepted"
    assert decision["strategy_delta"]["added"]
    strategy_record = json.loads(
        (tmp_path / "strategy_playbooks.jsonl").read_text(encoding="utf-8")
    )
    assert set(strategy_record["playbooks"]) == {"initial", "error"}
    assert calls[0]["tools"][0]["function"]["name"] == "update_prompt_component"
    assert calls[0]["tool_choice"]["function"]["name"] == "update_prompt_component"


def test_prompt_mutation_rejects_partial_all_update_atomically(tmp_path):
    baseline = baseline_bundle()
    adapter = CoverUpPromptAdapter(
        runner=SimpleNamespace(),
        candidate_dir=tmp_path,
        targets_by_split={},
        baseline=baseline,
        reflection_lm=lambda **kwargs: tool_call_response(
            "all",
            {"initial": baseline.initial},
            diagnosis="both stages failed",
            evidence=["both stages have failures"],
        ),
    )

    proposals = adapter.propose_new_texts(
        baseline.as_candidate(),
        {
            "initial": [{"Feedback": "initial failed"}],
            "error": [{"Feedback": "repair failed"}],
        },
        ["initial", "error"],
    )

    assert proposals == baseline.as_candidate()
    decision = json.loads(
        (tmp_path / "reflection_decisions.jsonl").read_text(encoding="utf-8")
    )
    assert decision["selection"] == "all"
    assert decision["status"] == "incomplete_replacements"


def test_prompt_mutation_selects_and_updates_component_in_one_call(tmp_path):
    baseline = baseline_bundle()
    calls = []
    improved = baseline.initial.replace(
        "Create new pytest test functions",
        "Inspect the causal failure first.\nCreate new pytest test functions",
    )

    def reflection_lm(**kwargs):
        calls.append(kwargs)
        return tool_call_response(
            "initial",
            {"initial": improved},
            diagnosis="inspect branch preconditions while preserving formatting",
            evidence=["the generated test missed the guarded branch"],
        )

    adapter = CoverUpPromptAdapter(
        runner=SimpleNamespace(),
        candidate_dir=tmp_path,
        targets_by_split={},
        baseline=baseline,
        reflection_lm=reflection_lm,
    )
    proposals = adapter.propose_new_texts(
        baseline.as_candidate(),
        {"initial": [{
            "Inputs": {"target": "pkg/a.py::first"},
            "Generated Outputs": {"execution_episodes": []},
            "Feedback": "a guarded branch remains",
        }]},
        ["initial"],
    )

    assert proposals["initial"].startswith(improved)
    assert proposals["initial"].count(STRATEGY_PLAYBOOK_BEGIN) == 1
    assert len(calls) == 1
    assert "`all` is always allowed" in calls[0]["messages"][-1]["content"]
    assert calls[0]["tools"][0]["type"] == "function"


def test_prompt_mutation_consolidates_inherited_strategy_without_duplicate_blocks(
    tmp_path,
):
    baseline = baseline_bundle()
    calls = []
    first_playbook = {
        "initial": {
            "observations": ["- First learned observation."],
            "decision_steps": ["1. First step.", "2) Second step."],
            "failure_modes": ["First failure mode."],
            "regression_guards": ["First regression guard."],
        },
    }
    second_playbook = {
        "initial": {
            "observations": [
                "First learned observation.",
                "Second contrastive observation.",
            ],
            "decision_steps": [
                "First refined step.",
                "Second refined step.",
                "Verify the observable branch effect.",
            ],
            "failure_modes": ["Second failure mode."],
            "regression_guards": ["Second regression guard."],
        },
    }

    def reflection_lm(**kwargs):
        calls.append(kwargs)
        playbooks = first_playbook if len(calls) == 1 else second_playbook
        return tool_call_response(
            "initial",
            {"initial": baseline.initial},
            playbooks=playbooks,
            strategy_delta={
                "added": ["Add contrastive reasoning."],
                "refined": [],
                "preserved": ["Preserve supported strategy."],
                "pruned": [],
            },
        )

    adapter = CoverUpPromptAdapter(
        runner=SimpleNamespace(),
        candidate_dir=tmp_path,
        targets_by_split={},
        baseline=baseline,
        reflection_lm=reflection_lm,
    )
    first = adapter.propose_new_texts(
        baseline.as_candidate(), {"initial": [{"Feedback": "first"}]}, ["initial"]
    )
    second = adapter.propose_new_texts(
        first, {"initial": [{"Feedback": "second"}]}, ["initial"]
    )

    assert second["initial"].count(STRATEGY_PLAYBOOK_BEGIN) == 1
    assert "1. 1." not in first["initial"]
    assert "- - First" not in first["initial"]
    assert "First learned observation." in second["initial"]
    assert "Second contrastive observation." in second["initial"]
    assert "First failure mode." not in second["initial"]
    assert STRATEGY_PLAYBOOK_BEGIN in calls[1]["messages"][-1]["content"]
    records = (tmp_path / "strategy_playbooks.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()
    assert len(records) == 2


def test_local_smoke_real_gepa_uses_one_call_all_flow(tmp_path):
    package_dir = tmp_path / "sample_repo" / "pkg"
    package_dir.mkdir(parents=True)
    (package_dir / "module.py").write_text(
        "def target(value):\n    return value + 1\n", encoding="utf-8"
    )
    baseline = baseline_bundle()
    improved_initial = "Analyze branch reachability first.\n" + baseline.initial
    improved_error = "Preserve valid test behavior during repair.\n" + baseline.error
    lm_calls = []

    class FakeRunner:
        config = SimpleNamespace(
            project_root=tmp_path,
            package_dir=package_dir,
            coverup_model="local-fake-coverup",
            max_attempts=2,
            repeat_tests=1,
            pytest_args="",
            max_concurrency=1,
            rate_limit=None,
        )

        def evaluate_batch(
            self, targets, prompt_path, *, candidate_id=None, split=None,
            workspace_kind="candidate",
        ):
            prompt = json.loads(Path(prompt_path).read_text(encoding="utf-8"))
            changed = prompt["initial"] != baseline.initial
            score = 0.8 if changed else 0.2
            results = []
            for target in targets:
                traces = [{
                    "attempt": 1,
                    "component": "initial",
                    "outcome": "test_error",
                    "generated_test": "def test_target(): assert missing_name",
                    "execution_error": "NameError: missing_name",
                    "next_component": "error",
                }, {
                    "attempt": 2,
                    "component": "error",
                    "outcome": "no_coverage_gain_unrepairable",
                    "generated_test": "def test_target(): assert True",
                    "remaining_lines": [2],
                    "remaining_branches": [],
                }]
                results.append(SimpleNamespace(
                    target=target,
                    score={
                        "score": score,
                        "statement_gain": score,
                        "branch_gain": 1.0,
                        "covered_statements": 8 if changed else 2,
                        "num_statements": 10,
                        "covered_branches": 0,
                        "num_branches": 0,
                        "valid": True,
                    },
                    feedback="local deterministic failure evidence",
                    attempt_traces=traces,
                ))
            return SimpleNamespace(
                run_id=f"local-{candidate_id}-{split}",
                tests_workspace=str(tmp_path / "generated" / str(candidate_id)),
                results=results,
                exit_code=0,
            )

    def reflection_lm(**kwargs):
        lm_calls.append(kwargs)
        return tool_call_response(
            "all",
            {"initial": improved_initial, "error": improved_error},
            diagnosis="generation and repair need a coordinated contract",
            evidence=["both attempts terminate without full coverage"],
        )

    train = [SymbolTarget("project", "pkg/module.py", "target", "train")]
    validation = [
        SymbolTarget("project", "pkg/module.py", "target", "validation")
    ]
    result = optimize(
        runner=FakeRunner(),
        train_targets=train,
        validation_targets=validation,
        baseline=baseline,
        reflection_lm=reflection_lm,
        artifacts_dir=tmp_path / "artifacts",
        auto=None,
        max_metric_calls=3,
    )

    assert len(lm_calls) == 1
    assert result.best_bundle.initial.startswith(improved_initial)
    assert result.best_bundle.error.startswith(improved_error)
    assert STRATEGY_PLAYBOOK_BEGIN in result.best_bundle.initial
    assert STRATEGY_PLAYBOOK_BEGIN in result.best_bundle.error
    decisions = (tmp_path / "artifacts" / "candidates" /
                 "reflection_decisions.jsonl").read_text(encoding="utf-8")
    decision = json.loads(decisions.splitlines()[-1])
    assert decision["one_call"] is True
    assert decision["selection"] == "all"
    assert decision["changed_components"] == ["initial", "error"]
    assert decision["status"] == "accepted"


def test_best_pareto_selector_uses_seventy_thirty_probability_boundary():
    class StubRandom:
        def __init__(self):
            self.values = iter((0.6999, 0.7))

        def random(self):
            return next(self.values)

    selector = BestParetoCandidateSelector(
        best_probability=0.7,
        rng=StubRandom(),
    )
    selector.best_selector = SimpleNamespace(select_candidate_idx=lambda state: 11)
    selector.pareto_selector = SimpleNamespace(select_candidate_idx=lambda state: 22)

    assert selector.select_candidate_idx(object()) == 11
    assert selector.select_candidate_idx(object()) == 22


def test_best_pareto_selector_can_use_pure_pareto():
    selector = BestParetoCandidateSelector(
        best_probability=0.0,
        rng=SimpleNamespace(random=lambda: 0.0),
    )
    selector.best_selector = SimpleNamespace(select_candidate_idx=lambda state: 11)
    selector.pareto_selector = SimpleNamespace(select_candidate_idx=lambda state: 22)

    assert selector.select_candidate_idx(object()) == 22


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
            "aggregate": {
                "score": 0.75,
                "statement_coverage": 0.75,
                "branch_coverage": 1.0,
            },
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
        gepa_seed=19,
        reflection_minibatch_size=3,
        reflection_temperature=0.2,
        best_candidate_probability=0.5,
    )

    assert captured["seed_candidate"] == baseline.as_candidate()
    assert set(captured["seed_candidate"]) == {"initial", "error"}
    assert captured["cache_evaluation"] is False
    assert captured["reflection_minibatch_size"] == 3
    assert captured["seed"] == 19
    assert isinstance(captured["module_selector"], LLMReflectionComponentSelector)
    assert isinstance(
        captured["candidate_selection_strategy"], BestParetoCandidateSelector
    )
    assert captured["candidate_selection_strategy"].best_probability == 0.5
    assert result.best_bundle == baseline
    assert result.as_dict()["optimizer_config"] == {
        "gepa_seed": 19,
        "reflection_minibatch_size": 3,
        "reflection_temperature": 0.2,
        "best_candidate_probability": 0.5,
        "max_metric_calls": 2,
    }


def test_tune_preflights_baseline_but_skips_proposal_when_gepa_keeps_it(
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
    events = []
    (tmp_path / "sample_repo" / "project" / "project").mkdir(parents=True)
    (tmp_path / "sample_repo" / "project" / "tests").mkdir(parents=True)

    monkeypatch.setattr(cli, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setenv("OPTIMIZE_MODEL", "fake-optimize-model")
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
        lambda **kwargs: (
            events.append("optimize")
            or SimpleNamespace(
                best_bundle=baseline,
                candidates=[baseline],
                validation_scores=[0.5],
                rerank={
                    "selected_digest": bundle_digest(baseline),
                    "top_k": 1,
                    "replicates": 3,
                    "leaderboard": [],
                },
                as_dict=lambda: {
                    "best_index": 0,
                    "best_candidate": baseline.as_candidate(),
                    "validation_scores": [0.5],
                    "total_metric_calls": 1,
                    "candidates": [baseline.as_candidate()],
                },
            )
        ),
    )
    baseline_result = {
        "target": test[0].__dict__,
        "score": 1.0,
        "coverage": {
            "valid": True,
            "score": 1.0,
            "covered_statements": 1,
            "num_statements": 1,
            "covered_branches": 0,
            "num_branches": 0,
        },
        "feedback": "ok",
    }
    monkeypatch.setattr(
        cli,
        "evaluate_bundle_repeated",
        lambda *args, **kwargs: (
            events.append("final baseline preflight")
            or {
                "results": [baseline_result],
                "aggregate": aggregate_coverage_score([baseline_result]),
                "run_ids": ["baseline-preflight"],
                "tests_workspaces": ["baseline-workspace"],
            }
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
        gepa_seed=7,
        reflection_minibatch_size=8,
        rerank_top_k=1,
        rerank_replicates=3,
        baseline_tests_dir=None,
        sample_repos_dir=Path("sample_repo"),
    )

    cli.tune(args)

    report = json.loads(
        (artifacts / "final_validation.json").read_text(encoding="utf-8")
    )
    assert report["final_evaluation_skipped"] is True
    assert report["skip_reason"].startswith("GEPA selected the unchanged baseline")
    assert report["final_split"] == "test"
    assert report["run_ids"] == []
    assert report["baseline_run_ids"] == ["baseline-preflight"]
    assert len(report["baseline_results"]) == 1
    assert report["candidate_rerank"]["selected_digest"] == bundle_digest(baseline)
    assert events == ["final baseline preflight", "optimize"]
    assert baseline_bundle().as_candidate() == json.loads(
        (artifacts / "prompts" / "gepa_optimized.json").read_text(encoding="utf-8")
    )


def test_tune_search_only_saves_program_without_opening_holdout(
    tmp_path, monkeypatch,
):
    from src.optimization import cli

    baseline = baseline_bundle()
    prompt_path = tmp_path / "baseline.json"
    baseline.save(prompt_path)
    artifacts = tmp_path / "artifacts"
    program_path = artifacts / "optimized_program_seed17.json"
    targets = {
        "train": [SymbolTarget("project", "pkg/a.py", "first", "train")],
        "validation": [
            SymbolTarget("project", "pkg/b.py", "second", "validation")
        ],
        "test": [SymbolTarget("project", "pkg/c.py", "third", "test")],
    }
    (tmp_path / "sample_repo" / "project" / "project").mkdir(parents=True)
    (tmp_path / "sample_repo" / "project" / "tests").mkdir(parents=True)
    events = []

    monkeypatch.setattr(cli, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setenv("OPTIMIZE_MODEL", "fake-optimize-model")
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
        "evaluate_bundle_repeated",
        lambda *args, **kwargs: pytest.fail("search-only opened the holdout"),
    )
    monkeypatch.setattr(
        cli,
        "optimize",
        lambda **kwargs: (
            events.append("optimize")
            or SimpleNamespace(
                as_dict=lambda: {
                    "best_index": 0,
                    "best_candidate": baseline.as_candidate(),
                    "validation_scores": [0.5],
                    "total_metric_calls": 1,
                    "optimizer_config": {"gepa_seed": 17},
                    "candidates": [baseline.as_candidate()],
                }
            )
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
        gepa_seed=17,
        reflection_minibatch_size=3,
        rerank_top_k=0,
        rerank_replicates=3,
        search_only=True,
        program_output=program_path,
        baseline_tests_dir=None,
        sample_repos_dir=Path("sample_repo"),
    )

    cli.tune(args)

    assert events == ["optimize"]
    assert json.loads(program_path.read_text(encoding="utf-8"))[
        "optimizer_config"
    ] == {"gepa_seed": 17}
    assert not (artifacts / "final_validation.json").exists()


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


def test_targeted_segmentation_selects_method_inside_small_class(tmp_path, monkeypatch):
    import importlib

    monkeypatch.syspath_prepend(str(Path("src").resolve()))
    segment_module = importlib.import_module("coverup.segment")
    source = tmp_path / "small.py"
    source.write_text(
        "class Small:\n"
        "    def first(self):\n"
        "        return 1\n"
        "\n"
        "    def target(self, value):\n"
        "        if value:\n"
        "            return True\n"
        "        return False\n",
        encoding="utf-8",
    )
    coverage = {
        "files": {
            str(source): {
                # A missing class-level statement appears before the target
                # method, reproducing the ordering that used to swallow it.
                "missing_lines": [1, 6, 7, 8],
                "executed_lines": [2, 3, 5],
                "missing_branches": [[6, 7], [6, 8]],
            }
        }
    }

    default_segments = segment_module.get_missing_coverage(coverage)
    targeted_segments = segment_module.get_missing_coverage(
        coverage, target_qualnames={"Small.target"}
    )

    assert [segment.qualname for segment in default_segments] == ["Small"]
    assert [segment.qualname for segment in targeted_segments] == ["Small.target"]


def test_coverup_no_final_coverage_still_runs_generation_setup(tmp_path, monkeypatch):
    import importlib

    monkeypatch.syspath_prepend(str(Path("src").resolve()))
    coverup_module = importlib.import_module("coverup.coverup")
    package_dir = tmp_path / "pkg"
    tests_dir = tmp_path / "tests"
    package_dir.mkdir()
    tests_dir.mkdir()
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    args = coverup_module.parse_args([
        "--package-dir", str(package_dir),
        "--tests-dir", str(tests_dir),
        "--model", "fake-model",
        "--log-file", str(tmp_path / "coverup.log"),
        "--no-checkpoint",
        "--no-final-coverage",
    ])
    coverage_calls = []
    chatter_instances = []

    class FakeChatter:
        def __init__(self, **kwargs):
            chatter_instances.append(kwargs)

        def __getattr__(self, name):
            if name.startswith("set_") or name == "add_function":
                return lambda *args, **kwargs: None
            raise AttributeError(name)

    class FakePrompter:
        @staticmethod
        def get_functions():
            return []

    class FakeProgress:
        def __init__(self, **kwargs):
            pass

        def update_cost(self, *args):
            pass

        def update_counters(self, *args):
            pass

        def close(self):
            pass

    def fake_measure_suite_coverage(**kwargs):
        coverage_calls.append(kwargs)
        return {"files": {}, "summary": {"percent_covered": 0.0}}

    monkeypatch.setattr(coverup_module, "parse_args", lambda: args)
    monkeypatch.setattr(coverup_module, "log_file", None)
    monkeypatch.setattr(coverup_module, "add_to_pythonpath", lambda path: None)
    monkeypatch.setattr(coverup_module.llm, "Chatter", FakeChatter)
    monkeypatch.setitem(
        coverup_module.prompter_registry, "gpt-v2", lambda cmd_args: FakePrompter()
    )
    monkeypatch.setattr(
        coverup_module, "measure_suite_coverage", fake_measure_suite_coverage
    )
    monkeypatch.setattr(coverup_module, "Progress", FakeProgress)
    monkeypatch.setattr(coverup_module, "get_required_modules", lambda: [])

    assert coverup_module.main() == 0
    coverup_module.log_file.close()
    assert chatter_instances == [{"model": "fake-model"}]
    # Initial coverage is needed to find missing segments; only the redundant
    # whole-suite pass after generation is skipped.
    assert len(coverage_calls) == 1


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


def test_test_salvage_iteratively_prunes_failing_statements(tmp_path, monkeypatch):
    import importlib

    monkeypatch.syspath_prepend(str(Path("src").resolve()))
    truncate = importlib.import_module(
        "coverup.testrunner"
    ).truncate_failing_test_module
    generated = """import pytest

def test_many_paths():
    with pytest.raises(ValueError):
        raise ValueError("expected")
    actual = 3
    assert actual == 4
    assert False

def test_independent():
    assert 2 + 2 == 4
"""
    failure_line = next(
        index
        for index, line in enumerate(generated.splitlines(), start=1)
        if "assert actual == 4" in line
    )

    first_salvage = truncate(
        generated,
        f"tmp_test_generated.py:{failure_line}: AssertionError",
    )

    assert first_salvage is not None
    assert "pytest.raises(ValueError)" in first_salvage
    assert "actual == 4" not in first_salvage
    assert "assert False" in first_salvage
    second_failure_line = next(
        index
        for index, line in enumerate(first_salvage.splitlines(), start=1)
        if "assert False" in line
    )
    second_salvage = truncate(
        first_salvage,
        f"tmp_test_generated.py:{second_failure_line}: AssertionError",
    )
    assert second_salvage is not None
    assert "assert False" not in second_salvage
    assert "test_independent" in second_salvage


def test_test_salvage_drops_only_scenario_dependent_on_failed_assignment(
    tmp_path, monkeypatch,
):
    import importlib

    monkeypatch.syspath_prepend(str(Path("src").resolve()))
    truncate = importlib.import_module(
        "coverup.testrunner"
    ).truncate_failing_test_module
    generated = """def test_many_scenarios():
    broken = build_invalid()
    broken.fit()
    assert broken.fitted
    independent = build_valid()
    independent.fit()
    assert independent.fitted
"""
    failure_line = next(
        index
        for index, line in enumerate(generated.splitlines(), start=1)
        if "broken =" in line
    )

    salvaged = truncate(
        generated,
        f"tmp_test_generated.py:{failure_line}: ValueError",
    )

    assert salvaged is not None
    assert "broken" not in salvaged
    assert "independent = build_valid()" in salvaged
    assert "assert independent.fitted" in salvaged


def test_test_salvage_removes_function_without_prior_assertion(tmp_path, monkeypatch):
    import importlib

    monkeypatch.syspath_prepend(str(Path("src").resolve()))
    truncate = importlib.import_module(
        "coverup.testrunner"
    ).truncate_failing_test_module
    generated = """def test_unverified_prefix():
    value = expensive_setup()
    assert value

def test_independent():
    assert True
"""
    failure_line = next(
        index
        for index, line in enumerate(generated.splitlines(), start=1)
        if "expensive_setup" in line
    )

    salvaged = truncate(
        generated,
        f"tmp_test_generated.py:{failure_line}: RuntimeError",
    )

    assert salvaged is not None
    assert "test_unverified_prefix" not in salvaged
    assert "test_independent" in salvaged


def test_coverup_salvages_verified_prefix_after_last_attempt(tmp_path, monkeypatch):
    import importlib
    import subprocess

    monkeypatch.syspath_prepend(str(Path("src").resolve()))
    coverup_module = importlib.import_module("coverup.coverup")
    testrunner_module = importlib.import_module("coverup.testrunner")
    monkeypatch.setattr(
        coverup_module,
        "state",
        SimpleNamespace(inc_counter=lambda key: None),
        raising=False,
    )
    monkeypatch.setattr(coverup_module, "test_seq", 1)
    coverage_calls = []
    generated = """import pytest

def test_target_paths():
    with pytest.raises(ValueError):
        raise ValueError("expected")
    assert missing_name
    assert False
"""

    async def fake_measure_test_coverage(**kwargs):
        coverage_calls.append(kwargs["test"])
        if len(coverage_calls) <= 3:
            failure_line = next(
                index
                for index, line in enumerate(kwargs["test"].splitlines(), start=1)
                if "assert missing_name" in line
            )
            raise subprocess.CalledProcessError(
                1,
                ["pytest"],
                output=(
                    f"tmp_test_generated.py:{failure_line}: "
                    "NameError: missing_name"
                ).encode(),
            )
        if "assert False" in kwargs["test"]:
            failure_line = next(
                index
                for index, line in enumerate(kwargs["test"].splitlines(), start=1)
                if "assert False" in line
            )
            raise subprocess.CalledProcessError(
                1,
                ["pytest"],
                output=(
                    f"tmp_test_generated.py:{failure_line}: AssertionError"
                ).encode(),
            )
        assert "missing_name" not in kwargs["test"]
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
    monkeypatch.setattr(
        testrunner_module, "measure_test_coverage", fake_measure_test_coverage
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
                        "content": f"```python\n{generated}\n```",
                    },
                }]
            }

    class Prompter:
        def initial_prompt(self, seg):
            return [{"role": "user", "content": "initial"}]

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
        repeat_tests=2,
        tests_dir=tmp_path,
        prefix="trace",
        isolate_tests=True,
        branch_coverage=True,
        show_details=False,
        save_coverage_to=None,
        salvage_failing_tests=True,
        salvage_max_prunes=4,
    )
    chatter = Chatter()

    result = asyncio.run(
        coverup_module.improve_coverage(args, chatter, Prompter(), segment)
    )
    traces = [
        json.loads(line)
        for line in args.trace_file.read_text(encoding="utf-8").splitlines()
    ]

    assert result is True
    assert chatter.calls == 3
    assert len(coverage_calls) == 5
    assert [trace["outcome"] for trace in traces] == [
        "test_error", "test_error", "test_error", "coverage_gain_saved",
    ]
    assert traces[-1]["component"] == "salvage"
    assert traces[-1]["salvaged_failures"] == 2
    saved = Path(traces[-1]["saved_test"]).read_text(encoding="utf-8")
    assert "pytest.raises(ValueError)" in saved
    assert "missing_name" not in saved


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
    seen_pytest_args = []

    async def fake_measure_test_coverage(**kwargs):
        nonlocal coverage_calls
        coverage_calls += 1
        seen_pytest_args.append(kwargs["pytest_args"])
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
        repeat_tests=2,
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
    assert seen_pytest_args == ["--count 2", "--count 2"]


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
        spec = json.loads(Path(
            command[command.index("--target-spec-file") + 1]
        ).read_text(encoding="utf-8"))[0]
        trace_path = Path(command[command.index("--trace-file") + 1])
        trace_path.write_text(
            json.dumps({
                "source_file": spec["source_file"],
                "symbol": spec["symbol"],
                "name": spec["symbol"],
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

    monkeypatch.setattr("src.optimization.runner.run_streamed", fake_subprocess_run)
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
    alpha_tests_dir = Path(alpha_command[alpha_command.index("--tests-dir") + 1])
    beta_tests_dir = Path(beta_command[beta_command.index("--tests-dir") + 1])
    assert alpha_tests_dir.parent.name == "target_workspaces"
    assert beta_tests_dir.parent.name == "target_workspaces"
    assert alpha_tests_dir != beta_tests_dir
    assert not alpha_tests_dir.exists()
    assert not beta_tests_dir.exists()
    persistent_workspace = Path(record.tests_workspace)
    assert {path.name for path in persistent_workspace.iterdir()} == {"alpha", "beta"}
    assert len(coverage_outputs) == 2
    assert {
        str(kwargs["package_dir"].resolve()) for kwargs in coverage_outputs
    } == {str(alpha_pkg.resolve()), str(beta_pkg.resolve())}
    assert {
        Path(kwargs["tests_dir"]).resolve() for kwargs in coverage_outputs
    } == {
        (persistent_workspace / "alpha").resolve(),
        (persistent_workspace / "beta").resolve(),
    }
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
        "src.optimization.runner.run_streamed",
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


def test_resolve_project_layouts_supports_single_project(tmp_path):
    repos = tmp_path / "src" / "sample_repo"
    (repos / "isort" / "isort").mkdir(parents=True)
    targets = [SymbolTarget("isort", "isort/a.py", "f", "train")]
    layouts = _resolve_project_layouts(
        tmp_path, targets, Path("src/sample_repo")
    )
    assert set(layouts) == {"isort"}
    assert layouts["isort"].tests_dir == repos / "isort" / "tests"
    assert not layouts["isort"].tests_dir.exists()


def test_resolve_project_layouts_builds_per_project_layouts(tmp_path):
    repos = tmp_path / "src" / "sample_repo"
    for project in ("isort", "mlxtend"):
        (repos / project / project).mkdir(parents=True)
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
    assert not layouts["mlxtend"].tests_dir.exists()


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
