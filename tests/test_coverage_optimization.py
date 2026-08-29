import asyncio
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import httpx
import openai
import pytest

from src.optimization.cli import (
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
from src.optimization.gepa import (
    MAX_OPTIMIZER_TEST_EXPERIMENTS,
    REFLECTION_MINIBATCH_SIZE,
    BestParetoCandidateSelector,
    CausalReflectionComponentSelector,
    CoverUpPromptAdapter,
    LLMReflectionComponentSelector,
    _definition_lines,
    build_coverage_report,
    bundle_digest,
    evaluate_bundle_batch_cached,
    evaluate_bundle_cached,
    log_reflection_request,
    optimize,
    validate_bundle,
    validate_reference_evaluation,
    validate_template,
)
from src.optimization.metrics import aggregate_coverage_score, build_feedback, score_symbol
from src.optimization.models import ExperimentConfig, ProjectLayout, SymbolTarget
from src.optimization.prompts import PromptBundle, baseline_bundle
from src.optimization.runner import (
    CoverUpExperimentRunner,
    _configure_runtime_environment,
    _package_dir_for_target,
    _saved_tests_for_target,
    _target_spec_source_file,
    _test_environment,
    _traces_for_target,
    _zero_coverage_like,
)
from src.optimization.subprocesses import run_streamed


def test_package_dir_for_target_narrows_nested_uploaded_source(tmp_path):
    source_root = tmp_path / "src"
    package = source_root / "fixture311"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("def target():\n    return 1\n", encoding="utf-8")
    target = SymbolTarget("project", "src/fixture311/__init__.py", "target")

    assert _package_dir_for_target(source_root, target) == package.resolve()


def test_package_dir_for_target_keeps_direct_python_source_root(tmp_path):
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "module.py").write_text("def target():\n    return 1\n", encoding="utf-8")
    target = SymbolTarget("project", "pkg/module.py", "target")

    assert _package_dir_for_target(package, target) == package.resolve()


def test_target_spec_source_file_matches_narrowed_package_base(tmp_path):
    package = tmp_path / "src" / "pkg" / "subpkg"
    package.mkdir(parents=True)
    target = SymbolTarget("project", "src/pkg/subpkg/module.py", "target")

    assert _target_spec_source_file(package, target) == "subpkg/module.py"


def test_definition_lines_finds_nested_functions_inside_control_flow():
    source = """\
def outer(metric):
    if metric == "first":
        def score(value):
            return value + 1
    else:
        def score(value):
            return value - 1
    return score(1)
"""

    lines = _definition_lines(source, "outer.score")

    assert {3, 4, 6, 7}.issubset(lines)


def tool_call_response(
    component,
    replacements,
    *,
    diagnosis="root cause",
    evidence=None,
    successful_experiment_ids=None,
):
    arguments = {
        "component": component,
        "replacements": replacements,
        "diagnosis": diagnosis,
        "evidence": evidence or ["observed failure"],
        "successful_experiment_ids": successful_experiment_ids or ["experiment-1"],
    }
    return [
        {
            "text": None,
            "tool_calls": [
                {
                    "type": "function",
                    "function": {
                        "name": "update_prompt_component",
                        "arguments": json.dumps(arguments),
                    },
                }
            ],
        }
    ]


def experiment_tool_call_response(
    case_id="case-1",
    test_module="def test_target():\n    assert True\n",
    hypothesis="replace the failed construction with a verified one",
):
    return [
        {
            "text": None,
            "tool_calls": [
                {
                    "type": "function",
                    "function": {
                        "name": "run_test_experiment",
                        "arguments": json.dumps(
                            {
                                "case_id": case_id,
                                "test_module": test_module,
                                "hypothesis": hypothesis,
                            }
                        ),
                    },
                }
            ],
        }
    ]


def requested_case_id(kwargs):
    content = kwargs["messages"][-1]["content"]
    match = re.search(r'"case_id":\s*"([^"]+)"', content)
    assert match
    return match.group(1)


def successful_experiment_id(kwargs):
    content = kwargs["messages"][-1]["content"]
    matches = re.findall(r'"experiment_id":\s*"([^"]+)"', content)
    assert matches
    return matches[-1]


class SuccessfulOptimizerExperimentRunner:
    def evaluate_optimizer_test(
        self,
        target,
        test_module,
        *,
        experiment_id,
    ):
        assert "def test_" in test_module
        return {
            "experiment_id": experiment_id,
            "target": target.__dict__,
            "pytest_passed": True,
            "pytest_exit_code": 0,
            "score": 1.0,
            "covered_statements": 2,
            "num_statements": 2,
            "covered_branches": 2,
            "num_branches": 2,
            "remaining_lines": [],
            "remaining_branches": [],
            "stdout": "2 passed",
        }


def runnable_reflection_record(
    *,
    target="pkg/a.py::first",
    score=0.2,
    feedback="a branch remains",
):
    return {
        "Inputs": {
            "target": target,
            "source_context": "1: def first(value):\n2:     return value + 1",
        },
        "Generated Outputs": {
            "candidate_score": score,
            "candidate_test": "def test_first(): assert missing_name",
            "execution_episodes": [],
        },
        "Feedback": feedback,
    }


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
        executed_lines=(1, 2),
        missing_lines=(3,),
        executed_branches=((1, 2),),
        missing_branches=((1, 3),),
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
        traces,
        target,
        workspace=workspace,
    )

    assert [trace["generated_test"] for trace in target_traces] == ["second feedback payload"]
    assert target_tests == [second_test.resolve()]


def test_run_coverage_exports_zero_coverage_when_pytest_collects_no_tests(
    tmp_path,
    monkeypatch,
):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if "json" in command:
            Path(command[command.index("-o") + 1]).write_text('{"files": {}}', encoding="utf-8")
            return SimpleNamespace(args=command, returncode=0, stdout="json written", stderr=None)
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
            Path(command[command.index("-o") + 1]).write_text('{"files": {}}', encoding="utf-8")
            return SimpleNamespace(args=command, returncode=0, stdout="json written", stderr=None)
        return SimpleNamespace(args=command, returncode=5, stdout="no tests ran", stderr=None)

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
    assert pytest_command[pytest_command.index("--basetemp") + 1] == str(pytest_basetemp.resolve())


def test_run_coverage_uses_selected_runtime_interpreter(tmp_path, monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(args=command, returncode=0, stdout="", stderr=None)

    monkeypatch.setattr("src.optimization.coveragepy.run_streamed", fake_run)
    package_dir = tmp_path / "pkg"
    tests_dir = tmp_path / "tests"
    package_dir.mkdir()
    tests_dir.mkdir()

    run_coverage(
        project_root=tmp_path,
        package_dir=package_dir,
        tests_dir=tests_dir,
        output=tmp_path / "coverage.json",
        env={"TESTGEN_PYTHON": "prepared-python"},
    )

    assert [command[0] for command in calls] == ["prepared-python", "prepared-python"]


@pytest.mark.skipif(os.name == "nt", reason="POSIX venv interpreters are symlinks")
def test_runtime_environment_preserves_venv_python_symlink(tmp_path):
    venv_python = tmp_path / ".venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.symlink_to(Path(sys.executable))
    environment = {"PATH": "/usr/bin"}

    _configure_runtime_environment(environment, venv_python)

    assert environment["TESTGEN_PYTHON"] == str(venv_python.absolute())
    assert environment["TESTGEN_PYTHON"] != str(venv_python.resolve())
    assert environment["VIRTUAL_ENV"] == str((tmp_path / ".venv").absolute())
    assert environment["PATH"].split(os.pathsep)[0] == str(venv_python.parent.absolute())


def test_parallel_coverage_subprocesses_use_isolated_pytest_state(tmp_path):
    package_dir = tmp_path / "pkg"
    tests_dir = tmp_path / "shared-tests"
    pytest_temp_root = tmp_path / "pytest-temp"
    package_dir.mkdir()
    tests_dir.mkdir()
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "module.py").write_text(
        "def first(value):\n    return value + 1\n\ndef second(value):\n    return value * 2\n",
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
    args = parser().parse_args(
        [
            "evaluate",
            "--dataset",
            "dataset.jsonl",
            "--prompt",
            "prompt.json",
        ]
    )

    assert args.repeat_tests == 5


def test_run_streamed_forwards_retains_and_unbuffers_output(capsys):
    completed = run_streamed(
        [
            sys.executable,
            "-u",
            "-c",
            ("import os; print('unbuffered=' + os.environ['PYTHONUNBUFFERED']); print('streamed-child-output')"),
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


def test_run_streamed_echoes_only_selected_child_lines(capsys):
    completed = run_streamed(
        [
            sys.executable,
            "-u",
            "-c",
            ("print('hidden detail'); print('PROMPTOPT_MODEL_ERROR {\"status_code\": 429}')"),
        ],
        echo=False,
        echo_prefixes=("PROMPTOPT_MODEL_ERROR ",),
    )

    assert "hidden detail" in completed.stdout
    visible = capsys.readouterr().out
    assert "hidden detail" not in visible
    assert 'PROMPTOPT_MODEL_ERROR {"status_code": 429}' in visible


def test_run_streamed_stops_process_at_timeout(capsys):
    started = time.monotonic()
    completed = run_streamed(
        [sys.executable, "-u", "-c", "import time; print('ready'); time.sleep(60)"],
        label="hanging worker",
        echo=False,
        announce=True,
        timeout=0.2,
    )

    assert time.monotonic() - started < 5
    assert completed.returncode == 124
    assert "ready" in completed.stdout
    assert "timed out after 0.2 seconds" in completed.stdout
    visible = capsys.readouterr().out
    assert "[hanging worker] started (timeout 0.2s)" in visible
    assert "[hanging worker] finished with exit code 124" in visible


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
    payload = output.removeprefix("PROMPTOPT_REFLECTION_REQUEST_BEGIN\n").removesuffix(
        "PROMPTOPT_REFLECTION_REQUEST_END\n"
    )
    assert json.loads(payload) == request


def test_optimizer_experiment_budget_matches_reflection_minibatch_cap():
    assert MAX_OPTIMIZER_TEST_EXPERIMENTS == REFLECTION_MINIBATCH_SIZE == 5


def test_coverup_chatter_returns_get_info_calls_with_results(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "src"))
    import coverup.llm as llm_module

    chatter = object.__new__(llm_module.Chatter)
    chatter._model = "fake-model"
    chatter._model_temperature = None
    chatter._default_max_tokens = 100
    chatter._extra_request_pars = None
    chatter._max_func_calls_per_chat = 3
    chatter.token_rate_limit = None
    chatter._add_cost = lambda cost: None
    chatter._log_msg = lambda ctx, message: None
    chatter._log_json = lambda ctx, payload: None
    chatter._signal_retry = lambda: None
    chatter._functions = {
        "get_info": {
            "function": lambda ctx, name: f"source:{ctx}:{name}",
            "schema": {
                "name": "get_info",
                "parameters": {"type": "object"},
            },
        }
    }

    tool_call = SimpleNamespace(
        id="call-1",
        function=SimpleNamespace(name="get_info", arguments=json.dumps({"name": "Helper"})),
    )

    class FakeMessage:
        def __init__(self, content, tool_calls):
            self.content = content
            self.tool_calls = tool_calls

        def model_dump(self, warnings=False):
            del warnings
            return {
                "role": "assistant",
                "content": self.content,
                "tool_calls": [
                    {
                        "id": call.id,
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in self.tool_calls
                ],
            }

    class FakeResponse:
        def __init__(self, finish_reason, message):
            self.choices = [SimpleNamespace(finish_reason=finish_reason, message=message)]

        def model_dump(self, warnings=False):
            del warnings
            return {
                "choices": [
                    {
                        "finish_reason": self.choices[0].finish_reason,
                        "message": self.choices[0].message.model_dump(),
                    }
                ]
            }

    responses = iter(
        (
            FakeResponse("tool_calls", FakeMessage(None, [tool_call])),
            FakeResponse("stop", FakeMessage("```python\nassert True\n```", [])),
        )
    )

    async def fake_send_request(request, ctx):
        del request, ctx
        return next(responses)

    chatter._send_request = fake_send_request
    monkeypatch.setattr(llm_module.litellm, "completion_cost", lambda response: 0)

    response = asyncio.run(chatter.chat([{"role": "user", "content": "write a test"}], ctx="target"))

    assert response["_coverup_tool_calls"] == [
        {
            "name": "get_info",
            "arguments": {"name": "Helper"},
            "result": "source:target:Helper",
        }
    ]


def test_coverup_logs_every_failed_model_call(monkeypatch, capsys):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "src"))
    import coverup.llm as llm_module

    chatter = object.__new__(llm_module.Chatter)
    chatter._model = "vertex_ai/test-model"
    chatter._max_backoff = 4
    chatter.token_rate_limit = None
    chatter._log_msg = lambda ctx, message: None
    chatter._signal_retry = lambda: None

    request = httpx.Request("POST", "https://example.invalid/v1/models/test")
    failures = iter(
        [
            openai.RateLimitError(
                "Resource exhausted",
                response=httpx.Response(429, request=request),
                body=None,
            ),
            openai.RateLimitError(
                "Resource exhausted",
                response=httpx.Response(429, request=request),
                body=None,
            ),
        ]
    )
    calls = 0

    async def fake_acreate(**request_args):
        nonlocal calls
        del request_args
        calls += 1
        if calls <= 2:
            raise next(failures)
        return "ok"

    async def no_sleep(delay):
        del delay

    monkeypatch.setattr(llm_module.litellm, "acreate", fake_acreate)
    monkeypatch.setattr(llm_module.asyncio, "sleep", no_sleep)

    response = asyncio.run(chatter._send_request({"messages": []}, ctx=None))

    assert response == "ok"
    events = [
        json.loads(line.removeprefix("PROMPTOPT_MODEL_ERROR "))
        for line in capsys.readouterr().out.splitlines()
        if line.startswith("PROMPTOPT_MODEL_ERROR ")
    ]
    assert [event["attempt"] for event in events] == [1, 2]
    assert all(event["model"] == "vertex_ai/test-model" for event in events)
    assert all(event["status_code"] == 429 for event in events)
    assert all(event["retrying"] is True for event in events)


def test_coverup_requests_durable_pause_after_repeated_429(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "src"))
    import coverup.llm as llm_module

    pause_path = tmp_path / "pause.json"
    monkeypatch.setenv("PROMPTOPT_PAUSE_FILE", str(pause_path))
    monkeypatch.setenv("PROMPTOPT_PAUSE_AFTER_429", "2")
    chatter = object.__new__(llm_module.Chatter)
    chatter._model = "vertex_ai/test-model"
    chatter._max_backoff = 4
    chatter.token_rate_limit = None
    chatter._log_msg = lambda ctx, message: None
    chatter._signal_retry = lambda: None
    request = httpx.Request("POST", "https://example.invalid/v1/models/test")

    async def fake_acreate(**request_args):
        del request_args
        raise openai.RateLimitError(
            "Resource exhausted",
            response=httpx.Response(429, request=request),
            body=None,
        )

    async def no_sleep(delay):
        del delay

    monkeypatch.setattr(llm_module.litellm, "acreate", fake_acreate)
    monkeypatch.setattr(llm_module.asyncio, "sleep", no_sleep)

    with pytest.raises(llm_module.ModelRateLimitPauseError):
        asyncio.run(chatter._send_request({"messages": []}, ctx=None))

    pause = json.loads(pause_path.read_text(encoding="utf-8"))
    assert pause["reason"] == "rate_limited"
    assert pause["attempt"] == 2
    assert pause["status_code"] == 429


def test_full_reflection_event_prints_only_when_enabled(monkeypatch, capsys):
    from src.optimization.gepa import log_full_reflection_event

    log_full_reflection_event("hidden", {"test_module": "def test_x(): pass"})
    assert capsys.readouterr().out == ""

    monkeypatch.setenv("PROMPTOPT_FULL_REFLECTION_LOGS", "true")
    log_full_reflection_event(
        "optimizer_test_execution",
        {"test_module": "def test_x(): pass", "stdout": "1 passed"},
    )

    output = capsys.readouterr().out
    assert output.startswith("PROMPTOPT_DEV_FULL_LOG_BEGIN\n")
    assert output.endswith("PROMPTOPT_DEV_FULL_LOG_END\n")
    payload = output.removeprefix("PROMPTOPT_DEV_FULL_LOG_BEGIN\n").removesuffix("PROMPTOPT_DEV_FULL_LOG_END\n")
    decoded = json.loads(payload)
    assert decoded["event"] == "optimizer_test_execution"
    assert decoded["payload"]["test_module"] == "def test_x(): pass"
    assert decoded["payload"]["stdout"] == "1 passed"


def test_cloud_reflection_logs_emit_compact_payloads(monkeypatch, capsys):
    from src.optimization.gepa import log_full_reflection_event, log_reflection_request

    monkeypatch.setenv("PROMPTOPT_COMPACT_LOGS", "true")
    request = {
        "messages": [{"role": "user", "content": "long evidence " + "x" * 5000}],
        "tools": [{"type": "function", "function": {"name": "run_test_experiment"}}],
        "tool_choice": {"type": "function", "function": {"name": "run_test_experiment"}},
    }
    log_reflection_request(request)
    output = capsys.readouterr().out
    assert "long evidence" not in output
    assert '"message_chars": 5014' in output
    assert '"run_test_experiment"' in output

    monkeypatch.setenv("PROMPTOPT_FULL_REFLECTION_LOGS", "true")
    log_full_reflection_event(
        "optimizer_test_execution",
        {"test_module": "def test_target():\n    " + "x" * 5000, "score": 0.5},
    )
    output = capsys.readouterr().out
    assert len(output) < 1000
    assert "xxxxx" not in output
    assert '"score": 0.5' in output
    assert '"test_module"' in output


def test_run_coverage_does_not_mask_real_pytest_failures(tmp_path, monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if "json" in command:
            Path(command[command.index("-o") + 1]).write_text('{"files": {}}', encoding="utf-8")
            return SimpleNamespace(args=command, returncode=0, stdout="json written", stderr=None)
        return SimpleNamespace(args=command, returncode=1, stdout="test failed", stderr=None)

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
    tmp_path,
    monkeypatch,
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
        kwargs["output"].write_text(
            json.dumps(
                {
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
                }
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=1, stdout="2 failed, 23 passed")

    monkeypatch.setattr("src.optimization.runner.run_coverage", fake_run_coverage)
    runner = CoverUpExperimentRunner(
        ExperimentConfig(
            project_root=tmp_path,
            package_dir=package_dir,
            tests_dir=tests_dir,
            artifacts_dir=artifacts_dir,
            coverup_model="fake-model",
        )
    )

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


@pytest.mark.parametrize(
    ("optimized", "baseline", "expected"),
    [(0.6, 0.5, True), (0.5, 0.5, False), (0.4, 0.5, False)],
)
def test_promotion_requires_strict_improvement(optimized, baseline, expected):
    assert should_promote(optimized_mean=optimized, baseline_mean=baseline) is expected


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
        specs = json.loads(Path(command[command.index("--target-spec-file") + 1]).read_text(encoding="utf-8"))
        target_specs.append(specs)
        spec = specs[0]
        trace_path = Path(command[command.index("--trace-file") + 1])
        trace_path.write_text(
            json.dumps(
                {
                    "source_file": spec["source_file"],
                    "symbol": spec["symbol"],
                    "name": spec["symbol"],
                    "component": "initial",
                    "outcome": "coverage_gain_saved",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stdout="coverup ok")

    def fake_run_coverage(**kwargs):
        return SimpleNamespace(returncode=1, stdout="no generated tests")

    monkeypatch.setattr("src.optimization.runner.run_streamed", fake_subprocess_run)
    monkeypatch.setattr("src.optimization.runner.run_coverage", fake_run_coverage)
    runner = CoverUpExperimentRunner(
        ExperimentConfig(
            project_root=tmp_path,
            package_dir=package_dir,
            tests_dir=tests_dir,
            artifacts_dir=artifacts_dir,
            coverup_model="fake-model",
        )
    )
    targets = [
        SymbolTarget("project", "pkg/a.py", "first", "train"),
        # Deliberately repeat the qualname in another file. Exact target specs and
        # per-target workspaces must prevent filename/counter races.
        SymbolTarget("project", "pkg/b.py", "first", "train"),
    ]
    stale_empty_workspace = artifacts_dir / "generated_tests" / "train" / "tests_candidate_candidate"
    stale_empty_workspace.mkdir(parents=True)

    record = runner.evaluate_batch(targets, prompt_path, candidate_id="candidate", split="train")
    baseline_record = runner.evaluate_batch(
        targets,
        prompt_path,
        candidate_id="baseline",
        split="train",
        workspace_kind="baseline",
    )

    assert len(commands) == 4
    assert {command[command.index("--target-symbols") + 1] for command in commands} == {"first"}
    assert all(len(spec) == 1 for spec in target_specs)
    assert {spec[0]["source_file"] for spec in target_specs} == {
        "pkg/a.py",
        "pkg/b.py",
    }
    assert len({command[command.index("--tests-dir") + 1] for command in commands}) == 4
    assert all(command[command.index("--max-concurrency") + 1] == "1" for command in commands)
    assert all("--trace-file" in command for command in commands)
    assert all("--no-final-coverage" in command for command in commands)
    assert Path(record.tests_workspace) == stale_empty_workspace.resolve()
    assert (
        Path(baseline_record.tests_workspace)
        == (artifacts_dir / "generated_tests" / "train" / "tests_base_line_baseline").resolve()
    )
    assert Path(record.tests_workspace).is_dir()
    assert len(record.results) == 2
    assert record.results[0].attempt_traces[0]["component"] == "initial"
    assert record.results[1].attempt_traces[0]["component"] == "initial"


@pytest.mark.parametrize("multi_project", [False, True])
def test_runner_resume_skips_targets_with_durable_checkpoints(tmp_path, monkeypatch, multi_project):
    from src.promptopt_pause import ModelRateLimitPauseError

    package_dir = tmp_path / "sample_repo" / "pkg"
    tests_dir = tmp_path / "sample_repo" / "tests"
    artifacts_dir = tmp_path / "artifacts"
    package_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)
    projects = None
    if multi_project:
        alpha_package = tmp_path / "sample_repo" / "alpha" / "pkg"
        beta_package = tmp_path / "sample_repo" / "beta" / "pkg"
        alpha_tests = tmp_path / "sample_repo" / "alpha" / "tests"
        beta_tests = tmp_path / "sample_repo" / "beta" / "tests"
        for path in (alpha_package, beta_package, alpha_tests, beta_tests):
            path.mkdir(parents=True)
        projects = {
            "alpha": ProjectLayout(alpha_package, alpha_tests),
            "beta": ProjectLayout(beta_package, beta_tests),
        }
    prompt_path = tmp_path / "prompt.json"
    baseline_bundle().save(prompt_path)
    pause_path = artifacts_dir / "pause_signal.json"
    monkeypatch.setenv("PROMPTOPT_PAUSE_FILE", str(pause_path))
    phase = {"resuming": False}
    calls = []

    def fake_subprocess_run(command, **kwargs):
        del kwargs
        symbol = command[command.index("--target-symbols") + 1]
        calls.append((phase["resuming"], symbol))
        if symbol == "second" and not phase["resuming"]:
            pause_path.parent.mkdir(parents=True, exist_ok=True)
            pause_path.write_text(json.dumps({"reason": "rate_limited"}), encoding="utf-8")
            return SimpleNamespace(returncode=1, stdout="HTTP 429")
        workspace = Path(command[command.index("--tests-dir") + 1])
        saved = workspace / "test_opt.py"
        saved.write_text(f"def test_{symbol}(): pass\n", encoding="utf-8")
        spec = json.loads(Path(command[command.index("--target-spec-file") + 1]).read_text(encoding="utf-8"))[0]
        Path(command[command.index("--trace-file") + 1]).write_text(
            json.dumps(
                {
                    "source_file": spec["source_file"],
                    "symbol": symbol,
                    "name": symbol,
                    "component": "initial",
                    "outcome": "coverage_gain_saved",
                    "saved_test": str(saved),
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stdout="ok")

    monkeypatch.setattr("src.optimization.runner.run_streamed", fake_subprocess_run)
    monkeypatch.setattr(
        "src.optimization.runner.run_coverage",
        lambda **kwargs: SimpleNamespace(returncode=1, stdout="no coverage"),
    )
    runner = CoverUpExperimentRunner(
        ExperimentConfig(
            project_root=tmp_path,
            package_dir=package_dir,
            tests_dir=tests_dir,
            artifacts_dir=artifacts_dir,
            coverup_model="fake-model",
            max_concurrency=1,
            projects=projects,
        )
    )
    target_projects = ("alpha", "beta") if multi_project else ("project", "project")
    targets = [
        SymbolTarget(target_projects[0], "pkg/a.py", "first", "train"),
        SymbolTarget(target_projects[1], "pkg/b.py", "second", "train"),
    ]

    with pytest.raises(ModelRateLimitPauseError):
        runner.evaluate_batch(targets, prompt_path, candidate_id="candidate", split="train")

    checkpoint_files = list((artifacts_dir / "runs" / "candidate" / "train").rglob("target_checkpoints/*.json"))
    assert len(checkpoint_files) == 1
    assert calls == [(False, "first"), (False, "second")]

    pause_path.unlink()
    phase["resuming"] = True
    monkeypatch.setenv("PROMPTOPT_RESUMING", "1")
    record = runner.evaluate_batch(targets, prompt_path, candidate_id="candidate", split="train")

    assert calls == [(False, "first"), (False, "second"), (True, "second")]
    assert [result.target.symbol for result in record.results] == ["first", "second"]
    assert len(list(Path(record.tests_workspace).rglob("test_opt_*.py"))) == 2


def test_runner_controlled_pause_occurs_after_completed_target_checkpoint(tmp_path, monkeypatch):
    from src.promptopt_pause import ModelRateLimitPauseError

    package_dir = tmp_path / "sample_repo" / "pkg"
    tests_dir = tmp_path / "sample_repo" / "tests"
    artifacts_dir = tmp_path / "artifacts"
    package_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)
    prompt_path = tmp_path / "prompt.json"
    baseline_bundle().save(prompt_path)
    pause_path = artifacts_dir / "pause_signal.json"
    monkeypatch.setenv("PROMPTOPT_PAUSE_FILE", str(pause_path))
    monkeypatch.setenv("PROMPTOPT_TEST_PAUSE_AFTER_COMPLETED_TARGETS", "1")
    calls = []

    def fake_subprocess_run(command, **kwargs):
        del kwargs
        calls.append(command[command.index("--target-symbols") + 1])
        workspace = Path(command[command.index("--tests-dir") + 1])
        saved = workspace / "test_opt.py"
        saved.write_text("def test_first(): pass\n", encoding="utf-8")
        spec = json.loads(Path(command[command.index("--target-spec-file") + 1]).read_text(encoding="utf-8"))[0]
        Path(command[command.index("--trace-file") + 1]).write_text(
            json.dumps(
                {
                    "source_file": spec["source_file"],
                    "symbol": "first",
                    "name": "first",
                    "component": "initial",
                    "outcome": "coverage_gain_saved",
                    "saved_test": str(saved),
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stdout="ok")

    monkeypatch.setattr("src.optimization.runner.run_streamed", fake_subprocess_run)
    monkeypatch.setattr(
        "src.optimization.runner.run_coverage",
        lambda **kwargs: SimpleNamespace(returncode=1, stdout="no coverage"),
    )
    runner = CoverUpExperimentRunner(
        ExperimentConfig(
            project_root=tmp_path,
            package_dir=package_dir,
            tests_dir=tests_dir,
            artifacts_dir=artifacts_dir,
            coverup_model="fake-model",
            max_concurrency=1,
        )
    )
    target = SymbolTarget("project", "pkg/a.py", "first", "train")

    with pytest.raises(ModelRateLimitPauseError, match="after 1 completed target"):
        runner.evaluate_batch([target], prompt_path, candidate_id="candidate", split="train")

    checkpoint_files = list((artifacts_dir / "runs" / "candidate" / "train").rglob("target_checkpoints/*.json"))
    assert len(checkpoint_files) == 1
    assert pause_path.is_file()
    assert calls == ["first"]

    pause_path.unlink()
    monkeypatch.setenv("PROMPTOPT_RESUMING", "1")
    record = runner.evaluate_batch([target], prompt_path, candidate_id="candidate", split="train")

    assert calls == ["first"]
    assert [result.target.symbol for result in record.results] == ["first"]


@pytest.mark.parametrize("split", ["train", "validation", "test"])
def test_runner_batches_generation_but_scores_and_reports_each_target_separately(
    tmp_path,
    monkeypatch,
    split,
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
        spec = json.loads(Path(command[command.index("--target-spec-file") + 1]).read_text(encoding="utf-8"))[0]
        generated_test = f"def test_{spec['symbol']}(): pass"
        test_path = workspace / "test_opt_1.py"
        test_path.write_text(generated_test + "\n", encoding="utf-8")
        trace_path = Path(command[command.index("--trace-file") + 1])
        trace_path.write_text(
            json.dumps(
                {
                    "source_file": spec["source_file"],
                    "symbol": spec["symbol"],
                    "name": spec["symbol"],
                    "component": "initial",
                    "outcome": "coverage_gain_saved",
                    "generated_test": generated_test,
                    "saved_test": str(test_path),
                }
            )
            + "\n",
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
        kwargs["output"].write_text(
            json.dumps(
                {
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
                }
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(
            returncode=0 if first else 1,
            stdout="first passed" if first else "second-target failure",
        )

    monkeypatch.setattr("src.optimization.runner.run_streamed", fake_subprocess_run)
    monkeypatch.setattr("src.optimization.runner.run_coverage", fake_run_coverage)
    runner = CoverUpExperimentRunner(
        ExperimentConfig(
            project_root=tmp_path,
            package_dir=package_dir,
            tests_dir=tests_dir,
            artifacts_dir=artifacts_dir,
            coverup_model="fake-model",
            max_concurrency=2,
        )
    )
    targets = [
        SymbolTarget("project", "pkg/a.py", "first", split),
        SymbolTarget("project", "pkg/b.py", "second", split),
    ]

    record = runner.evaluate_batch(
        targets,
        prompt_path,
        candidate_id="candidate",
        split=split,
    )

    assert len(coverup_commands) == 2
    assert {command[command.index("--target-symbols") + 1] for command in coverup_commands} == {"first", "second"}
    assert all(command[command.index("--max-concurrency") + 1] == "1" for command in coverup_commands)
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
    tmp_path,
    monkeypatch,
):
    package_dir = tmp_path / "sample_repo" / "pkg"
    package_dir.mkdir(parents=True)
    (package_dir / "a.py").write_text("def first(value):\n    return value + 1\n", encoding="utf-8")
    (package_dir / "b.py").write_text(
        "def second(value):\n    if value:\n        return 1\n    return 0\n",
        encoding="utf-8",
    )
    artifacts_dir = tmp_path / "artifacts"
    coverup_commands = []

    def fake_subprocess_run(command, **kwargs):
        coverup_commands.append(command)
        workspace = Path(command[command.index("--tests-dir") + 1])
        spec = json.loads(Path(command[command.index("--target-spec-file") + 1]).read_text(encoding="utf-8"))[0]
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
        kwargs["output"].write_text(
            json.dumps(
                {
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
                }
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stdout=f"{spec['symbol']} passed")

    monkeypatch.setattr("src.optimization.runner.run_streamed", fake_subprocess_run)
    monkeypatch.setattr("src.optimization.runner.run_coverage", fake_run_coverage)
    runner = CoverUpExperimentRunner(
        ExperimentConfig(
            project_root=tmp_path,
            package_dir=package_dir,
            tests_dir=tmp_path / "sample_repo" / "tests",
            artifacts_dir=artifacts_dir,
            coverup_model="local-fake-model",
            max_concurrency=2,
        )
    )
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
        targets,
        baseline.as_candidate(),
        capture_traces=True,
    )
    reflective = adapter.make_reflective_dataset(
        baseline.as_candidate(),
        evaluated,
        ["initial"],
    )["initial"]

    assert len(coverup_commands) == 2
    assert {command[command.index("--target-symbols") + 1] for command in coverup_commands} == {"first", "second"}
    assert len(list((artifacts_dir / "generated_tests" / "train").iterdir())) == 1
    assert [output["target"]["symbol"] for output in evaluated.outputs] == [
        "first",
        "second",
    ]
    rows_by_target = {row["Inputs"]["target"]: row for row in reflective}
    assert set(rows_by_target) == {"pkg/b.py::second"}
    assert rows_by_target["pkg/b.py::second"]["Generated Outputs"]["candidate_test"] == "def test_second(): pass"
    assert "Remaining lines: [3, 4]" in rows_by_target["pkg/b.py::second"]["Feedback"]


def test_runner_salvages_measured_scores_after_coverup_process_failure(
    tmp_path,
    monkeypatch,
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
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="provider returned an empty response"),
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
    runner = CoverUpExperimentRunner(
        ExperimentConfig(
            project_root=tmp_path,
            package_dir=package_dir,
            tests_dir=tests_dir,
            artifacts_dir=artifacts_dir,
            coverup_model="fake-model",
        )
    )

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
    (baseline_tests / "test_existing.py").write_text("def test_existing(): pass\n", encoding="utf-8")

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
    runner = CoverUpExperimentRunner(
        ExperimentConfig(
            project_root=tmp_path,
            package_dir=package_dir,
            tests_dir=tmp_path / "sample_repo" / "tests",
            artifacts_dir=artifacts_dir,
            coverup_model="fake-model",
        )
    )
    target = SymbolTarget("project", "pkg/module.py", "target", "validation")

    record = runner.evaluate_existing_tests_batch([target], baseline_tests, split="validation")

    assert record.tests_workspace == str(baseline_tests.resolve())
    assert record.results[0].score["score"] == pytest.approx(0.5)
    assert record.results[0].score["valid"] is True


def test_optimizer_test_experiment_runs_in_separate_teacher_workspace(tmp_path):
    package_dir = tmp_path / "sample_repo" / "pkg"
    package_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "module.py").write_text(
        "def target(value):\n    if value > 0:\n        return 'positive'\n    return 'other'\n",
        encoding="utf-8",
    )
    artifacts = tmp_path / "artifacts"
    runner = CoverUpExperimentRunner(
        ExperimentConfig(
            project_root=tmp_path,
            package_dir=package_dir,
            tests_dir=tmp_path / "sample_repo" / "tests",
            artifacts_dir=artifacts,
            coverup_model="unused",
            repeat_tests=0,
        )
    )
    target = SymbolTarget("project", "pkg/module.py", "target", "train")

    result = runner.evaluate_optimizer_test(
        target,
        "from pkg.module import target\n\n"
        "def test_positive():\n"
        "    assert target(1) == 'positive'\n\n"
        "def test_other():\n"
        "    assert target(0) == 'other'\n",
        experiment_id="teacher-case-1",
    )

    experiment_dir = artifacts / "optimizer_experiments" / "teacher-case-1"
    assert result["pytest_passed"] is True
    assert result["score"] == 1.0
    assert result["covered_branches"] == result["num_branches"] == 2
    assert (experiment_dir / "test_optimizer_experiment.py").is_file()
    assert (experiment_dir / "result.json").is_file()
    assert not (artifacts / "generated_tests").exists()


def test_score_symbol_uses_statement_and_branch_gain():
    before = coverage(
        executed_lines=(1,),
        missing_lines=(2, 3),
        executed_branches=((1, 2),),
        missing_branches=((2, 3), (2, 4)),
    )
    after = coverage(
        executed_lines=(1, 2),
        missing_lines=(3,),
        executed_branches=((1, 2), (2, 3)),
        missing_branches=((2, 4),),
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
        {
            "score": score_symbol(
                coverage(missing_lines=(1,), missing_branches=((1, 2),)),
                coverage(executed_lines=(1,), executed_branches=((1, 2),)),
            ).as_dict()
        },
        {
            "score": score_symbol(
                coverage(missing_lines=tuple(range(10)), missing_branches=tuple((i, i + 1) for i in range(10))),
                coverage(missing_lines=tuple(range(10)), missing_branches=tuple((i, i + 1) for i in range(10))),
            ).as_dict()
        },
    ]

    aggregate = aggregate_coverage_score(results)

    assert aggregate["statement_coverage"] == pytest.approx(1 / 11)
    assert aggregate["branch_coverage"] == pytest.approx(1 / 11)
    assert aggregate["score"] == pytest.approx(1 / 11)


def test_aggregate_score_weights_branch_at_seventy_percent():
    aggregate = aggregate_coverage_score(
        [
            {
                "coverage": {
                    "valid": True,
                    "covered_statements": 10,
                    "num_statements": 10,
                    "covered_branches": 0,
                    "num_branches": 10,
                }
            }
        ]
    )

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
    reference = [
        {
            "target": target,
            "coverage": score_symbol(
                coverage(missing_lines=(1,), missing_branches=((1, 2),)),
                coverage(executed_lines=(1,), executed_branches=((1, 2),)),
            ).as_dict(),
        }
    ]

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

    result = symbol_coverage(load_report(report_path), "isort/parse.py", "file_contents")

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
    assert set(bundle.as_candidate()) == {"initial", "error", "missing_coverage"}
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
            self,
            targets,
            candidate,
            *,
            candidate_id=None,
            split=None,
            workspace_kind="candidate",
        ):
            self.calls += 1
            self.candidate_id = candidate_id
            return SimpleNamespace(
                run_id="run-1",
                tests_workspace="tests-candidate",
                results=[
                    SimpleNamespace(
                        target=target,
                        score={"score": 0.75},
                        feedback="cached feedback",
                    )
                    for target in targets
                ],
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
            self,
            targets,
            candidate,
            *,
            candidate_id=None,
            split=None,
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
                results=[
                    SimpleNamespace(
                        target=target,
                        score={"score": 0.5},
                        feedback="ok",
                    )
                    for target in targets
                ],
            )

    runner = ConcurrentRunner()
    bundle = baseline_bundle()
    targets = [
        SymbolTarget("project", "pkg/a.py", "first"),
        SymbolTarget("project", "pkg/b.py", "second"),
    ]

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda target: evaluate_bundle_cached(runner, target, bundle, tmp_path, targets),
                targets,
            )
        )

    assert [result["score"] for result in results] == [0.5, 0.5]
    assert runner.max_active == 1
    assert runner.calls == 1


def test_batch_evaluation_deduplicates_repeated_minibatch_targets(tmp_path):
    class DuplicateDetectingRunner:
        def __init__(self):
            self.config = SimpleNamespace(max_concurrency=2, rate_limit=None)
            self.candidate_ids = []

        def evaluate_batch(
            self,
            targets,
            candidate,
            *,
            candidate_id=None,
            split=None,
            workspace_kind="candidate",
        ):
            self.candidate_ids.append(candidate_id)
            return SimpleNamespace(
                run_id="run-once",
                tests_workspace="tests-candidate",
                results=[
                    SimpleNamespace(
                        target=targets[0],
                        score={"score": 0.5},
                        feedback="ok",
                    )
                ],
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
            self,
            targets,
            candidate,
            *,
            candidate_id=None,
            split=None,
            workspace_kind="candidate",
        ):
            self.calls.append(split)
            return SimpleNamespace(
                run_id=f"run-{split}",
                tests_workspace=f"tests_candidate_{candidate_id}_{split}",
                results=[
                    SimpleNamespace(
                        target=target,
                        score={"score": 0.25},
                        feedback=split,
                    )
                    for target in targets
                ],
            )

    runner = SplitRunner()
    bundle = baseline_bundle()
    train = SymbolTarget("project", "pkg/train.py", "train_target", "train")
    validation = SymbolTarget("project", "pkg/validation.py", "validation_target", "validation")

    train_result = evaluate_bundle_cached(runner, train, bundle, tmp_path, [train])
    validation_result = evaluate_bundle_cached(runner, validation, bundle, tmp_path, [validation])

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
            self,
            targets,
            candidate,
            *,
            candidate_id=None,
            split=None,
            workspace_kind="candidate",
        ):
            self.calls.append(candidate_id)
            results = []
            for target in targets:
                value = 0.2 if target.symbol == "first" else 0.8
                covered = int(value * 10)
                results.append(
                    SimpleNamespace(
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
                        attempt_traces=[
                            {
                                "attempt": 1,
                                "component": "initial",
                                "outcome": "coverage_gain_saved",
                                "generated_test": f"def test_{target.symbol}(): pass",
                            }
                        ],
                    )
                )
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

    evaluated = adapter.evaluate(targets, baseline.as_candidate(), capture_traces=True)
    reflective = adapter.make_reflective_dataset(baseline.as_candidate(), evaluated, ["initial"])

    assert evaluated.scores == pytest.approx([0.2, 0.8])
    assert len(runner.calls) == 2
    assert len(set(runner.calls)) == 2
    assert all(call.startswith(bundle_digest(baseline) + "-") for call in runner.calls)
    assert sum(call.endswith("-r1") for call in runner.calls) == 1
    assert "pkg/a.py::first" == reflective["initial"][0]["Inputs"]["target"]
    assert "def first" in reflective["initial"][0]["Inputs"]["source_context"]
    assert (
        reflective["initial"][0]["Generated Outputs"]["execution_episodes"][0]["initial_attempts"][0]["generated_test"]
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
        return [
            {
                "results": [
                    {
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
                    }
                    for target in requested
                ],
            }
        ]

    adapter._evaluate_replicates = fake_evaluate_replicates
    evaluated = adapter.evaluate([targets[1]], baseline.as_candidate(), capture_traces=False)

    assert evaluated_target_batches == [[targets[1]]]
    assert [output["target"]["symbol"] for output in evaluated.outputs] == ["second"]


def test_direct_gepa_adapter_objectives_aggregate_to_micro_coverage(tmp_path):
    targets = [
        SymbolTarget("project", "pkg/a.py", "small", "validation"),
        SymbolTarget("project", "pkg/b.py", "large", "validation"),
    ]
    adapter = CoverUpPromptAdapter(
        runner=SimpleNamespace(),
        candidate_dir=tmp_path / "candidates",
        targets_by_split={"validation": targets},
        baseline=baseline_bundle(),
        reflection_lm=lambda prompt: ["<template>unchanged</template>"],
    )

    def fake_evaluate_replicates(requested, bundle, *, split):
        assert requested == targets
        return [
            {
                "results": [
                    {
                        "target": targets[0].__dict__,
                        "score": 1.0,
                        "coverage": {
                            "valid": True,
                            "covered_statements": 1,
                            "num_statements": 1,
                            "covered_branches": 1,
                            "num_branches": 1,
                            "statement_gain": 1.0,
                            "branch_gain": 1.0,
                        },
                    },
                    {
                        "target": targets[1].__dict__,
                        "score": 0.0,
                        "coverage": {
                            "valid": True,
                            "covered_statements": 0,
                            "num_statements": 99,
                            "covered_branches": 0,
                            "num_branches": 99,
                            "statement_gain": 0.0,
                            "branch_gain": 0.0,
                        },
                    },
                ],
            }
        ]

    adapter._evaluate_replicates = fake_evaluate_replicates
    evaluated = adapter.evaluate(targets, adapter.baseline.as_candidate(), capture_traces=False)

    statement = sum(objective["statement_coverage"] for objective in evaluated.objective_scores) / len(
        evaluated.objective_scores
    )
    branch = sum(objective["branch_coverage"] for objective in evaluated.objective_scores) / len(
        evaluated.objective_scores
    )
    score = sum(evaluated.scores) / len(evaluated.scores)

    assert statement == pytest.approx(0.01)
    assert branch == pytest.approx(0.01)
    assert score == pytest.approx(0.3 * statement + 0.7 * branch)


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
            self,
            targets,
            prompt_template,
            *,
            candidate_id=None,
            split=None,
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
                    "candidate": 0.8,
                    "parent": 0.6,
                    "baseline": 0.4,
                },
                "regressed_target": {
                    "candidate": 0.2,
                    "parent": 0.8,
                    "baseline": 0.9,
                },
            }
            results = []
            for target in targets:
                value = scores[target.symbol][version]
                covered = int(value * 10)
                results.append(
                    SimpleNamespace(
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
                        attempt_traces=[
                            {
                                "attempt": 1,
                                "component": "initial",
                                "outcome": "coverage_gain_saved",
                                "generated_test": f"def test_{version}_{target.symbol}(): pass",
                            }
                        ],
                    )
                )
            return SimpleNamespace(
                run_id=f"run-{candidate_id}",
                tests_workspace=f"tests-{candidate_id}",
                results=results,
            )

    baseline = baseline_bundle()
    parent_initial = baseline.initial.replace(
        "Create new pytest test functions",
        "Parent marker: preserve verified behavior.\nCreate new pytest test functions",
    )
    proposed_initial = parent_initial.replace(
        "Parent marker: preserve verified behavior.",
        "Parent marker: preserve verified behavior.\nContrastive marker: compare causal outcomes.",
    )
    adapter = CoverUpPromptAdapter(
        runner=FakeRunner(),
        candidate_dir=tmp_path / "candidates",
        targets_by_split={},
        baseline=baseline,
        reflection_lm=None,
    )
    parent = {**baseline.as_candidate(), "initial": parent_initial}
    candidate = {**parent, "initial": proposed_initial}
    adapter.candidate_lineage[bundle_digest(PromptBundle.from_candidate(parent))] = {
        "parent_candidate": baseline.as_candidate(),
        "changed_components": ["initial"],
    }
    adapter.candidate_lineage[bundle_digest(PromptBundle.from_candidate(candidate))] = {
        "parent_candidate": parent,
        "changed_components": ["initial"],
    }
    targets = [
        SymbolTarget("project", "pkg/a.py", "improved_target", "train"),
        SymbolTarget("project", "pkg/b.py", "regressed_target", "train"),
    ]
    adapter.targets_by_split = {"train": targets}

    evaluated = adapter.evaluate(targets, candidate, capture_traces=True)
    reflective = adapter.make_reflective_dataset(candidate, evaluated, ["initial"])["initial"]
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

    assert [row["Generated Outputs"]["exemplar_type"] for row in reflective[:2]] == ["regression", "positive"]
    trace_path = tmp_path / "candidates" / "reflection_traces.jsonl"
    trace = json.loads(trace_path.read_text(encoding="utf-8").splitlines()[-1])
    assert trace["schema_version"] == 2
    assert trace["candidate_digest"] == bundle_digest(PromptBundle.from_candidate(candidate))
    assert trace["components_to_update"] == ["initial"]
    assert [row["Generated Outputs"]["exemplar_type"] for row in trace["records"]["initial"][:2]] == [
        "regression",
        "positive",
    ]


def test_reflection_uses_only_trajectories_that_exercised_component(tmp_path):
    baseline = baseline_bundle()
    adapter = CoverUpPromptAdapter(
        runner=SimpleNamespace(),
        candidate_dir=tmp_path,
        targets_by_split={},
        baseline=baseline,
        reflection_lm=lambda prompt: pytest.fail("no evidence must not invoke the LM"),
    )
    evaluation = SimpleNamespace(
        trajectories=[
            {
                "target": {
                    "source_file": "pkg/a.py",
                    "symbol": "first",
                },
                "score": 0.25,
                "replicate_scores": [0.25],
                "feedback": "missing branches",
                "source_context": "def first(): ...",
                "attempt_traces": [
                    {
                        "attempt": 1,
                        "component": "error",
                        "outcome": "test_error",
                        "generated_test": "def test_first(): ...",
                        "execution_error": "AssertionError",
                    }
                ],
            }
        ]
    )

    reflective = adapter.make_reflective_dataset(baseline.as_candidate(), evaluation, ["error", "initial"])

    assert len(reflective["error"]) == 1
    assert reflective["initial"] == []
    unchanged = adapter.propose_new_texts(baseline.as_candidate(), reflective, ["initial"])
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
    evaluation = SimpleNamespace(
        trajectories=[
            {
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
                        "get_info_calls": [
                            {
                                "name": "get_info",
                                "arguments": {"name": "helper"},
                                "result": "def helper(): return 1",
                            }
                        ],
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
                        "get_info_calls": [
                            {
                                "name": "get_info",
                                "arguments": {"name": "factory"},
                                "result": "def factory(): return helper()",
                            }
                        ],
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
            }
        ]
    )

    row = adapter.make_reflective_dataset(baseline.as_candidate(), evaluation, ["error"])["error"][0]
    output = row["Generated Outputs"]
    episode = output["execution_episodes"][0]

    assert "baseline_test" not in output
    assert episode["initial_attempts"][0]["generated_test"].startswith("def test_initial")
    assert episode["initial_attempts"][0]["get_info_calls"][0]["arguments"] == {"name": "helper"}
    assert len(episode["repair_transitions"]) == 2
    first, second = episode["repair_transitions"]
    assert first["failing_test"].startswith("def test_initial")
    assert first["error"] == "NameError: broken"
    assert first["repaired_test"].startswith("def test_repair_one")
    assert first["execution_error_after"] == "NameError: still_broken"
    assert first["get_info_calls"][0]["result"].startswith("def factory")
    assert second["failing_test"].startswith("def test_repair_one")
    assert second["error"] == "NameError: still_broken"
    assert second["repaired_test"].startswith("def test_repair_two")
    assert second["outcome"] == "coverage_gain_saved"


def test_causal_component_selector_prefers_terminal_error_failures():
    selector = CausalReflectionComponentSelector()
    candidate = baseline_bundle().as_candidate()
    trajectories = [
        {
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
        }
    ]

    selected = selector(None, trajectories, [0.2], 0, candidate)

    assert selected == ["error"]


def test_causal_component_selector_never_selects_unexercised_error():
    selector = CausalReflectionComponentSelector()
    candidate = baseline_bundle().as_candidate()
    trajectories = [
        {
            "score": 0.1,
            "attempt_traces": [
                {
                    "attempt": 1,
                    "component": "initial",
                    "outcome": "no_coverage_gain_unrepairable",
                }
            ],
        }
    ]

    selected = selector(None, trajectories, [0.1], 0, candidate)

    assert selected == ["initial"]


def test_causal_component_selector_returns_noop_without_failure_evidence():
    selector = CausalReflectionComponentSelector()
    candidate = baseline_bundle().as_candidate()
    trajectories = [
        {
            "score": 1.0,
            "attempt_traces": [
                {
                    "attempt": 1,
                    "component": "initial",
                    "outcome": "coverage_gain_saved",
                    "gained_lines": [1],
                    "remaining_lines": [],
                    "gained_branches": [],
                    "remaining_branches": [],
                }
            ],
        }
    ]

    selected = selector(None, trajectories, [1.0], 0, candidate)

    assert selected == []


def test_llm_component_selector_always_exposes_both_after_any_failure():
    selector = LLMReflectionComponentSelector()
    candidate = baseline_bundle().as_candidate()
    trajectories = [
        {
            "score": 0.1,
            "attempt_traces": [
                {"component": "initial", "outcome": "test_error"},
            ],
        }
    ]

    selected = selector(None, trajectories, [0.1], 0, candidate)

    assert selected == ["initial", "error", "missing_coverage"]


def test_component_update_parser_accepts_native_tool_call_objects_only():
    response = tool_call_response(
        "initial",
        {"initial": baseline_bundle().initial},
        diagnosis="preserve reachability constraints",
        evidence=["the initial attempt missed a branch"],
    )
    arguments = json.loads(response[0]["tool_calls"][0]["function"]["arguments"])
    native_response = [
        {
            "text": None,
            "tool_calls": [
                SimpleNamespace(
                    function=SimpleNamespace(
                        name="update_prompt_component",
                        arguments=json.dumps(arguments),
                    )
                )
            ],
        }
    ]

    parsed = CoverUpPromptAdapter._extract_component_update(native_response)

    assert parsed == arguments
    assert CoverUpPromptAdapter._extract_component_update([json.dumps(arguments)]) is None


def test_component_update_parser_rejects_missing_successful_experiment():
    incomplete = {
        "component": "initial",
        "replacements": {"initial": baseline_bundle().initial},
        "diagnosis": "a narrow patch without a reusable strategy",
        "evidence": ["one branch was missed"],
    }
    response = [
        {
            "text": None,
            "tool_calls": [
                {
                    "function": {
                        "name": "update_prompt_component",
                        "arguments": json.dumps(incomplete),
                    },
                }
            ],
        }
    ]

    assert CoverUpPromptAdapter._extract_component_update(response) is None


def test_prompt_mutation_runs_successful_test_before_updating_all_components(tmp_path):
    baseline = baseline_bundle()
    improved_initial = baseline.initial.replace(
        "Create new pytest test functions",
        "Analyze reachability first.\nCreate new pytest test functions",
    )
    improved_error = "Coordinate repair with initial constraints.\n" + baseline.error
    improved_missing_coverage = "Improve missing coverage as well.\n" + baseline.missing_coverage
    calls = []

    def reflection_lm(**kwargs):
        calls.append(kwargs)
        if kwargs["tools"][0]["function"]["name"] == "run_test_experiment":
            return experiment_tool_call_response(requested_case_id(kwargs))
        return tool_call_response(
            "all",
            {"initial": improved_initial, "error": improved_error, "missing_coverage": improved_missing_coverage},
            diagnosis="generation and repair use inconsistent constraints",
            evidence=["both stages have terminal failures"],
            successful_experiment_ids=[successful_experiment_id(kwargs)],
        )

    target = SymbolTarget("project", "pkg/a.py", "first", "train")
    adapter = CoverUpPromptAdapter(
        runner=SuccessfulOptimizerExperimentRunner(),
        candidate_dir=tmp_path,
        targets_by_split={"train": [target]},
        baseline=baseline,
        reflection_lm=reflection_lm,
    )
    proposals = adapter.propose_new_texts(
        baseline.as_candidate(),
        {
            "initial": [runnable_reflection_record()],
            "error": [],
        },
        list(baseline.as_candidate().keys()),
    )

    assert proposals["initial"] == improved_initial
    assert proposals["error"] == improved_error
    assert proposals["missing_coverage"] == improved_missing_coverage
    assert len(calls) == 2
    decision = json.loads((tmp_path / "reflection_decisions.jsonl").read_text(encoding="utf-8"))
    assert decision["experiment_first"] is True
    assert decision["optimizer_calls"] == 2
    assert decision["selection"] == "all"
    assert decision["changed_components"] == ["initial", "error", "missing_coverage"]
    assert decision["status"] == "accepted"
    assert decision["successful_experiment_ids"]
    lesson = json.loads((tmp_path / "experiment_lessons.jsonl").read_text(encoding="utf-8"))
    assert lesson["successful_experiment_ids"] == decision["successful_experiment_ids"]
    assert calls[0]["tools"][0]["function"]["name"] == "run_test_experiment"
    assert calls[1]["tools"][0]["function"]["name"] == "update_prompt_component"


def test_prompt_mutation_rejects_partial_all_update_atomically(tmp_path):
    baseline = baseline_bundle()
    target = SymbolTarget("project", "pkg/a.py", "first", "train")

    def reflection_lm(**kwargs):
        if kwargs["tools"][0]["function"]["name"] == "run_test_experiment":
            return experiment_tool_call_response(requested_case_id(kwargs))
        return tool_call_response(
            "all",
            {"initial": baseline.initial},
            diagnosis="both stages failed",
            evidence=["both stages have failures"],
            successful_experiment_ids=[successful_experiment_id(kwargs)],
        )

    adapter = CoverUpPromptAdapter(
        runner=SuccessfulOptimizerExperimentRunner(),
        candidate_dir=tmp_path,
        targets_by_split={"train": [target]},
        baseline=baseline,
        reflection_lm=reflection_lm,
    )

    proposals = adapter.propose_new_texts(
        baseline.as_candidate(),
        {
            "initial": [runnable_reflection_record()],
            "error": [],
        },
        list(baseline.as_candidate().keys()),
    )

    assert proposals == baseline.as_candidate()
    decision = json.loads((tmp_path / "reflection_decisions.jsonl").read_text(encoding="utf-8"))
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
        if kwargs["tools"][0]["function"]["name"] == "run_test_experiment":
            return experiment_tool_call_response(requested_case_id(kwargs))
        return tool_call_response(
            "initial",
            {"initial": improved},
            diagnosis="inspect branch preconditions while preserving formatting",
            evidence=["the generated test missed the guarded branch"],
            successful_experiment_ids=[successful_experiment_id(kwargs)],
        )

    target = SymbolTarget("project", "pkg/a.py", "first", "train")
    adapter = CoverUpPromptAdapter(
        runner=SuccessfulOptimizerExperimentRunner(),
        candidate_dir=tmp_path,
        targets_by_split={"train": [target]},
        baseline=baseline,
        reflection_lm=reflection_lm,
    )
    proposals = adapter.propose_new_texts(
        baseline.as_candidate(),
        {"initial": [runnable_reflection_record()]},
        ["initial"],
    )

    assert proposals["initial"] == improved
    assert len(calls) == 2
    update_prompt = calls[1]["messages"][-1]["content"]
    assert "`all` is always allowed" in update_prompt
    assert "Use one strategy consistently: Reflexion" in update_prompt
    assert "suitable for a less-capable test-generation model" in update_prompt
    assert "<REFLECTION>...</REFLECTION>" in update_prompt
    assert "exactly one fenced `python` block" in update_prompt
    assert "trigger, action, and verification criterion" in update_prompt
    assert adapter.max_component_chars["initial"] >= 2_400
    assert adapter.max_component_chars["error"] >= 1_600
    assert calls[0]["tools"][0]["type"] == "function"


def test_prompt_remains_unchanged_when_optimizer_cannot_prove_a_better_test(tmp_path):
    baseline = baseline_bundle()
    calls = []

    class FailedExperimentRunner:
        def evaluate_optimizer_test(
            self,
            target,
            test_module,
            *,
            experiment_id,
        ):
            return {
                "experiment_id": experiment_id,
                "target": target.__dict__,
                "pytest_passed": False,
                "pytest_exit_code": 1,
                "score": 0.0,
                "stdout": "AssertionError",
            }

    def reflection_lm(**kwargs):
        calls.append(kwargs)
        return experiment_tool_call_response(requested_case_id(kwargs))

    target = SymbolTarget("project", "pkg/a.py", "first", "train")
    adapter = CoverUpPromptAdapter(
        runner=FailedExperimentRunner(),
        candidate_dir=tmp_path,
        targets_by_split={"train": [target]},
        baseline=baseline,
        reflection_lm=reflection_lm,
    )
    proposals = adapter.propose_new_texts(
        baseline.as_candidate(),
        {"initial": [runnable_reflection_record()]},
        ["initial"],
    )

    assert proposals == {"initial": baseline.initial}
    assert len(calls) == 5
    decision = json.loads((tmp_path / "reflection_decisions.jsonl").read_text(encoding="utf-8"))
    assert decision["status"] == "no_successful_test_experiment"
    assert not (tmp_path / "experiment_lessons.jsonl").exists()


def test_local_smoke_real_gepa_uses_one_call_all_flow(tmp_path):
    package_dir = tmp_path / "sample_repo" / "pkg"
    package_dir.mkdir(parents=True)
    (package_dir / "module.py").write_text("def target(value):\n    return value + 1\n", encoding="utf-8")
    baseline = baseline_bundle()
    improved_initial = "Analyze branch reachability first.\n" + baseline.initial
    improved_error = "Preserve valid test behavior during repair.\n" + baseline.error
    improved_missing_coverage = "Preserve valid test behavior during extension.\n" + baseline.missing_coverage
    lm_calls = []

    class FakeRunner:
        config = SimpleNamespace(
            project_root=tmp_path,
            package_dir=package_dir,
            coverup_model="local-fake-coverup",
            max_attempts=2,
            repeat_tests=0,
            pytest_args="",
            max_concurrency=1,
            rate_limit=None,
        )

        def evaluate_batch(
            self,
            targets,
            prompt_path,
            *,
            candidate_id=None,
            split=None,
            workspace_kind="candidate",
        ):
            prompt = json.loads(Path(prompt_path).read_text(encoding="utf-8"))
            changed = prompt["initial"] != baseline.initial
            score = 0.8 if changed else 0.2
            results = []
            for target in targets:
                traces = [
                    {
                        "attempt": 1,
                        "component": "initial",
                        "outcome": "test_error",
                        "generated_test": "def test_target(): assert missing_name",
                        "execution_error": "NameError: missing_name",
                        "next_component": "error",
                    },
                    {
                        "attempt": 2,
                        "component": "error",
                        "outcome": "no_coverage_gain_unrepairable",
                        "generated_test": "def test_target(): assert True",
                        "remaining_lines": [2],
                        "remaining_branches": [],
                    },
                ]
                results.append(
                    SimpleNamespace(
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
                    )
                )
            return SimpleNamespace(
                run_id=f"local-{candidate_id}-{split}",
                tests_workspace=str(tmp_path / "generated" / str(candidate_id)),
                results=results,
                exit_code=0,
            )

        def evaluate_optimizer_test(
            self,
            target,
            test_module,
            *,
            experiment_id,
        ):
            return {
                "experiment_id": experiment_id,
                "target": target.__dict__,
                "pytest_passed": True,
                "pytest_exit_code": 0,
                "score": 1.0,
                "covered_statements": 10,
                "num_statements": 10,
                "covered_branches": 0,
                "num_branches": 0,
                "stdout": "1 passed",
            }

    def reflection_lm(**kwargs):
        lm_calls.append(kwargs)
        if kwargs["tools"][0]["function"]["name"] == "run_test_experiment":
            return experiment_tool_call_response(requested_case_id(kwargs))
        return tool_call_response(
            "all",
            {"initial": improved_initial, "error": improved_error, "missing_coverage": improved_missing_coverage},
            diagnosis="generation and repair need a coordinated contract",
            evidence=["both attempts terminate without full coverage"],
            successful_experiment_ids=[successful_experiment_id(kwargs)],
        )

    train = [SymbolTarget("project", "pkg/module.py", "target", "train")]
    validation = [SymbolTarget("project", "pkg/module.py", "target", "validation")]
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

    assert len(lm_calls) == 2
    assert result.best_bundle.initial == improved_initial
    assert result.best_bundle.error == improved_error
    assert result.best_bundle.missing_coverage == improved_missing_coverage
    decisions = (tmp_path / "artifacts" / "candidates" / "reflection_decisions.jsonl").read_text(encoding="utf-8")
    decision = json.loads(decisions.splitlines()[-1])
    assert decision["experiment_first"] is True
    assert decision["selection"] == "all"
    assert decision["changed_components"] == ["initial", "error", "missing_coverage"]
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
    train = [SymbolTarget("project", f"pkg/{index}.py", f"target_{index}", "train") for index in range(8)]
    validation = [SymbolTarget("project", "pkg/b.py", "second", "validation")]

    result = optimize(
        runner=SimpleNamespace(),
        train_targets=train,
        validation_targets=validation,
        baseline=baseline,
        reflection_lm=lambda prompt: [prompt],
        artifacts_dir=tmp_path,
        auto=None,
        max_metric_calls=2,
        reflection_minibatch_size=3,
    )

    assert captured["seed_candidate"] == baseline.as_candidate()
    assert set(captured["seed_candidate"]) == {"initial", "error", "missing_coverage"}
    assert captured["cache_evaluation"] is False
    assert captured["reflection_minibatch_size"] == 3
    assert isinstance(captured["module_selector"], LLMReflectionComponentSelector)
    assert isinstance(captured["candidate_selection_strategy"], BestParetoCandidateSelector)
    assert captured["candidate_selection_strategy"].best_probability == 0.7
    assert result.best_bundle == baseline


def test_optimize_only_samples_train_targets_below_full_coverage(
    tmp_path,
    monkeypatch,
):
    baseline = baseline_bundle()
    captured = {}

    def fake_gepa_optimize(**kwargs):
        captured.update(kwargs)
        seed = kwargs["seed_candidate"]
        return SimpleNamespace(
            best_candidate=seed,
            best_idx=0,
            candidates=[seed],
            val_aggregate_scores=[0.8],
            total_metric_calls=2,
        )

    def fake_preflight(runner, targets, *args, split, **kwargs):
        del runner, args, kwargs
        results = []
        for target in targets:
            score = 0.4 if target.symbol in {"target_1", "target_3"} else 1.0
            results.append(
                {
                    "target": target.__dict__,
                    "score": score,
                    "coverage": {
                        "valid": True,
                        "score": score,
                        "num_statements": 2,
                        "num_branches": 1,
                    },
                    "feedback": "ok",
                }
            )
        return {
            "results": results,
            "aggregate": {
                "score": 0.8,
                "statement_coverage": 0.8,
                "branch_coverage": 0.8,
            },
        }

    monkeypatch.setattr("src.optimization.gepa.gepa_core.optimize", fake_gepa_optimize)
    monkeypatch.setattr(
        "src.optimization.gepa.evaluate_bundle_repeated",
        fake_preflight,
    )
    train = [SymbolTarget("project", f"pkg/{index}.py", f"target_{index}", "train") for index in range(6)]
    validation = [SymbolTarget("project", "pkg/validation.py", "validation", "validation")]

    optimize(
        runner=SimpleNamespace(),
        train_targets=train,
        validation_targets=validation,
        baseline=baseline,
        reflection_lm=lambda prompt: [prompt],
        artifacts_dir=tmp_path,
        auto=None,
        max_metric_calls=2,
    )

    assert [target.symbol for target in captured["trainset"]] == [
        "target_1",
        "target_3",
    ]
    assert captured["reflection_minibatch_size"] == 2


def test_tune_preflights_baseline_but_skips_proposal_when_gepa_keeps_it(
    tmp_path,
    monkeypatch,
):
    from src.optimization import cli

    baseline = baseline_bundle()
    prompt_path = tmp_path / "baseline.json"
    baseline.save(prompt_path)
    artifacts = tmp_path / "artifacts"
    train = [SymbolTarget("project", "pkg/a.py", "first", "train")]
    validation = [SymbolTarget("project", "pkg/b.py", "second", "validation")]
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
        lambda args, projects=None: SimpleNamespace(config=SimpleNamespace(artifacts_dir=artifacts)),
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
        reflection_minibatch_size=5,
        auto=None,
        max_metric_calls=1,
        evaluation_replicates=1,
        baseline_tests_dir=None,
        sample_repos_dir=Path("sample_repo"),
    )

    cli.tune(args)

    report = json.loads((artifacts / "final_validation.json").read_text(encoding="utf-8"))
    assert report["final_evaluation_skipped"] is True
    assert report["skip_reason"].startswith("GEPA selected the unchanged baseline")
    assert report["final_split"] == "test"
    assert report["reflection_minibatch_size"] == 5
    assert report["run_ids"] == []
    assert report["baseline_run_ids"] == ["baseline-preflight"]
    assert len(report["baseline_results"]) == 1
    assert events == ["final baseline preflight", "optimize"]
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


def test_coverup_no_final_coverage_still_runs_generation_setup(tmp_path, monkeypatch):
    import importlib

    monkeypatch.syspath_prepend(str(Path("src").resolve()))
    coverup_module = importlib.import_module("coverup.coverup")
    package_dir = tmp_path / "pkg"
    tests_dir = tmp_path / "tests"
    package_dir.mkdir()
    tests_dir.mkdir()
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    args = coverup_module.parse_args(
        [
            "--package-dir",
            str(package_dir),
            "--tests-dir",
            str(tests_dir),
            "--model",
            "fake-model",
            "--log-file",
            str(tmp_path / "coverup.log"),
            "--no-checkpoint",
            "--no-final-coverage",
        ]
    )
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
    monkeypatch.setitem(coverup_module.prompter_registry, "gpt-v2", lambda cmd_args: FakePrompter())
    monkeypatch.setattr(coverup_module, "measure_suite_coverage", fake_measure_suite_coverage)
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
        validate_reference_evaluation(
            [
                {
                    "target": {
                        "project": "project",
                        "source_file": "pkg/missing.py",
                        "symbol": "target",
                        "split": "validation",
                    },
                    "coverage": None,
                    "feedback": "Replicate 0:\nScore: 0. Coverage lookup failed",
                }
            ]
        )


def test_coverup_separates_reflection_from_executable_python(monkeypatch):
    import importlib

    monkeypatch.syspath_prepend(str(Path("src").resolve()))
    coverup_module = importlib.import_module("coverup.coverup")
    response = """<REFLECTION>
Exercise the false branch with a sentinel and verify the returned state.
</REFLECTION>
```python
def test_false_branch():
    assert True
```"""

    reflection, code = coverup_module.extract_response_parts(response)

    assert reflection == ("Exercise the false branch with a sentinel and verify the returned state.")
    assert code == "def test_false_branch():\n    assert True\n"
    assert "REFLECTION" not in coverup_module.extract_python(response)
    with pytest.raises(RuntimeError, match="exactly one"):
        coverup_module.extract_response_parts("```python\nassert True\n```\n```python\nassert False\n```")


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
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": None},
                    }
                ]
            }

    class MinimalPrompter:
        def initial_prompt(self, seg):
            return [{"role": "user", "content": "write tests"}]

    chatter = EmptyChatter()
    result = asyncio.run(
        coverup_module.improve_coverage(
            SimpleNamespace(
                dry_run=False,
                max_attempts=1,
                log_file=str(tmp_path / "coverup.log"),
            ),
            chatter,
            MinimalPrompter(),
            SimpleNamespace(name="target"),
        )
    )

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
    seen_pytest_args = []

    async def fake_measure_test_coverage(**kwargs):
        nonlocal coverage_calls
        coverage_calls += 1
        seen_pytest_args.append(kwargs["pytest_args"])
        if coverage_calls == 1:
            raise subprocess.CalledProcessError(1, ["pytest"], output=b"AssertionError: wrong result")
        return {
            "files": {
                "pkg/a.py": {
                    "executed_lines": [2],
                    "executed_branches": [],
                }
            }
        }

    monkeypatch.setattr(coverup_module, "measure_test_coverage", fake_measure_test_coverage)

    class Chatter:
        calls = 0

        async def chat(self, messages, *, ctx=None):
            self.calls += 1
            code = "assert False" if self.calls == 1 else "assert True"
            return {
                "_coverup_tool_calls": [
                    {
                        "name": "get_info",
                        "arguments": {"name": f"dependency_{self.calls}"},
                        "result": f"source for dependency {self.calls}",
                    }
                ],
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": (f"<REFLECTION>repair plan {self.calls}</REFLECTION>\n```python\n{code}\n```"),
                        },
                    }
                ],
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

    result = asyncio.run(coverup_module.improve_coverage(args, Chatter(), Prompter(), segment))
    traces = [json.loads(line) for line in args.trace_file.read_text(encoding="utf-8").splitlines()]

    assert result is True
    assert [trace["component"] for trace in traces] == ["initial", "error"]
    assert [trace["outcome"] for trace in traces] == [
        "test_error",
        "coverage_gain_saved",
    ]
    assert traces[0]["execution_error"] == "AssertionError: wrong result"
    assert traces[1]["generated_test"].strip() == "assert True"
    assert traces[0]["model_reflection"] == "repair plan 1"
    assert traces[1]["model_reflection"] == "repair plan 2"
    assert "REFLECTION" not in traces[1]["generated_test"]
    assert traces[0]["get_info_calls"] == [
        {
            "name": "get_info",
            "arguments": {"name": "dependency_1"},
            "result": "source for dependency 1",
        }
    ]
    assert traces[1]["get_info_calls"][0]["arguments"]["name"] == "dependency_2"
    assert seen_pytest_args == ["--count 2", "--count 2"]


def test_coverup_retries_passing_incomplete_coverage_with_lines_branches_and_context(
    tmp_path,
    monkeypatch,
):
    import importlib

    monkeypatch.syspath_prepend(str(Path("src").resolve()))
    coverup_module = importlib.import_module("coverup.coverup")
    prompt_module = importlib.import_module("coverup.prompt.gpt_v2")
    monkeypatch.setattr(
        coverup_module,
        "state",
        SimpleNamespace(inc_counter=lambda key: None),
        raising=False,
    )
    monkeypatch.setattr(coverup_module, "test_seq", 1)

    source = tmp_path / "pkg" / "a.py"
    source.parent.mkdir()
    source.write_text(
        "def target(value):\n    if value:\n        return 1\n    return 0\n",
        encoding="utf-8",
    )
    segment = importlib.import_module("coverup.segment").CodeSegment(
        source,
        "target",
        1,
        5,
        "target",
        lines_of_interest={2, 3, 4},
        missing_lines={3},
        executed_lines=set(),
        missing_branches={(2, 4)},
        context=[],
        imports=[],
    )

    coverage_calls = 0

    async def fake_measure_test_coverage(**kwargs):
        nonlocal coverage_calls
        coverage_calls += 1
        executed_lines = [1] if coverage_calls == 1 else [1, 2, 3]
        executed_branches = [] if coverage_calls == 1 else [[2, 4]]
        return {
            "files": {
                str(source.resolve()): {
                    "executed_lines": executed_lines,
                    "executed_branches": executed_branches,
                }
            }
        }

    monkeypatch.setattr(coverup_module, "measure_test_coverage", fake_measure_test_coverage)

    args = SimpleNamespace(
        dry_run=False,
        max_attempts=2,
        log_file=str(tmp_path / "coverup.log"),
        trace_file=tmp_path / "attempt_trace.jsonl",
        install_missing_modules=False,
        pytest_args="",
        repeat_tests=0,
        tests_dir=tmp_path / "tests",
        prefix="coverage",
        isolate_tests=True,
        branch_coverage=True,
        show_details=False,
        save_coverage_to=None,
        src_base_dir=tmp_path,
        prompt_template_file=None,
    )
    args.tests_dir.mkdir()
    prompter = prompt_module.GptV2Prompter(args)

    class Chatter:
        def __init__(self):
            self.calls = 0
            self.messages = []

        async def chat(self, messages, *, ctx=None):
            self.calls += 1
            self.messages.append([dict(message) for message in messages])
            code = (
                "def test_target():\n    assert True"
                if self.calls == 1
                else "def test_target():\n    assert target(True) == 1"
            )
            return {
                "_coverup_tool_calls": [],
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": f"```python\n{code}\n```",
                        },
                    }
                ],
            }

    chatter = Chatter()
    result = asyncio.run(coverup_module.improve_coverage(args, chatter, prompter, segment))
    traces = [json.loads(line) for line in args.trace_file.read_text(encoding="utf-8").splitlines()]

    assert result is True
    assert coverage_calls == 2
    assert chatter.calls == 2
    assert traces[0]["outcome"] == "coverage_incomplete"
    assert traces[0]["gained_lines"] == []
    assert traces[0]["gained_branches"] == []
    assert traces[0]["remaining_lines"] == [3]
    assert traces[0]["remaining_branches"] == [[2, 4]]
    assert traces[1]["outcome"] == "coverage_gain_saved"
    assert traces[1]["gained_branches"] == [[2, 4]]
    assert traces[1]["remaining_lines"] == []
    assert traces[1]["remaining_branches"] == []

    retry_messages = chatter.messages[1]
    assert any(message["role"] == "assistant" and "assert True" in message["content"] for message in retry_messages)
    missing_prompt = retry_messages[-1]["content"]
    assert "The tests still lack coverage: line 3 and branch 2->4 do not execute." in missing_prompt


def test_coverup_matches_absolute_generated_coverage_to_relative_segment(tmp_path, monkeypatch):
    import importlib

    monkeypatch.syspath_prepend(str(Path("src").resolve()))
    coverup_module = importlib.import_module("coverup.coverup")
    source = tmp_path / "outside-workdir" / "pkg" / "a.py"
    source.parent.mkdir(parents=True)
    source.write_text("def target():\n    return 1\n", encoding="utf-8")
    segment = SimpleNamespace(filename="pkg/a.py", path=source)

    result = coverup_module._coverage_for_segment(
        {
            "files": {
                str(source.resolve()): {
                    "executed_lines": [1, 2],
                    "executed_branches": [],
                }
            }
        },
        segment,
    )

    assert result == {"executed_lines": [1, 2], "executed_branches": []}


def test_coverup_matches_relative_generated_coverage_from_project_import_root(tmp_path, monkeypatch):
    import importlib

    monkeypatch.syspath_prepend(str(Path("src").resolve()))
    coverup_module = importlib.import_module("coverup.coverup")
    import_root = tmp_path / "uploaded-project"
    source = import_root / "pkg" / "a.py"
    source.parent.mkdir(parents=True)
    source.write_text("def target():\n    return 1\n", encoding="utf-8")
    monkeypatch.chdir(import_root)
    segment = SimpleNamespace(filename=str(source), path=source)

    result = coverup_module._coverage_for_segment(
        {
            "files": {
                "pkg/a.py": {
                    "executed_lines": [1, 2],
                    "executed_branches": [],
                }
            }
        },
        segment,
    )

    assert result == {"executed_lines": [1, 2], "executed_branches": []}


def test_coverup_stops_after_no_gain_without_a_third_prompt_component(
    tmp_path,
    monkeypatch,
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

    monkeypatch.setattr(coverup_module, "measure_test_coverage", fake_measure_test_coverage)

    class Chatter:
        calls = 0

        async def chat(self, messages, *, ctx=None):
            self.calls += 1
            return {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": "```python\nassert True\n```",
                        },
                    }
                ]
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

    result = asyncio.run(coverup_module.improve_coverage(args, chatter, Prompter(), segment))
    trace = json.loads(args.trace_file.read_text(encoding="utf-8").splitlines()[0])

    assert result is True
    assert chatter.calls == 1
    assert trace["component"] == "initial"
    assert trace["outcome"] == "no_coverage_gain_unrepairable"
    assert trace["coverage_files"] == ["pkg/a.py"]
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
    coverup_working_directories = []
    coverage_outputs = []

    def fake_subprocess_run(command, **kwargs):
        commands.append(command)
        coverup_working_directories.append(Path(kwargs["cwd"]).resolve())
        spec = json.loads(Path(command[command.index("--target-spec-file") + 1]).read_text(encoding="utf-8"))[0]
        trace_path = Path(command[command.index("--trace-file") + 1])
        trace_path.write_text(
            json.dumps(
                {
                    "source_file": spec["source_file"],
                    "symbol": spec["symbol"],
                    "name": spec["symbol"],
                    "component": "initial",
                    "outcome": "coverage_gain_saved",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stdout="coverup ok")

    def fake_run_coverage(**kwargs):
        coverage_outputs.append(kwargs)
        symbol = "first" if kwargs["package_dir"] == alpha_pkg else "Second.method"
        source_file = "alpha/a.py" if symbol == "first" else "beta/b.py"
        kwargs["output"].write_text(
            json.dumps(
                {
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
                }
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stdout="coverage ok")

    monkeypatch.setattr("src.optimization.runner.run_streamed", fake_subprocess_run)
    monkeypatch.setattr("src.optimization.runner.run_coverage", fake_run_coverage)
    runner = CoverUpExperimentRunner(
        ExperimentConfig(
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
        )
    )
    targets = [
        SymbolTarget("beta", "beta/b.py", "Second.method", "train"),
        SymbolTarget("alpha", "alpha/a.py", "first", "train"),
    ]

    record = runner.evaluate_batch(targets, prompt_path, candidate_id="candidate", split="train")

    assert len(commands) == 2
    alpha_command = next(command for command in commands if command[command.index("--target-symbols") + 1] == "first")
    beta_command = next(
        command for command in commands if command[command.index("--target-symbols") + 1] == "Second.method"
    )
    assert Path(alpha_command[alpha_command.index("--package-dir") + 1]).resolve() == alpha_pkg.resolve()
    assert Path(beta_command[beta_command.index("--package-dir") + 1]).resolve() == beta_pkg.resolve()
    assert set(coverup_working_directories) == {
        alpha_pkg.parent.resolve(),
        beta_pkg.parent.resolve(),
    }
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
    assert {str(kwargs["package_dir"].resolve()) for kwargs in coverage_outputs} == {
        str(alpha_pkg.resolve()),
        str(beta_pkg.resolve()),
    }
    assert {Path(kwargs["tests_dir"]).resolve() for kwargs in coverage_outputs} == {
        (persistent_workspace / "alpha").resolve(),
        (persistent_workspace / "beta").resolve(),
    }
    assert [result.target.symbol for result in record.results] == [
        "Second.method",
        "first",
    ]
    assert all(result.score["score"] == 1.0 for result in record.results)


def test_existing_baseline_tests_are_scored_per_project(tmp_path, monkeypatch):
    alpha_pkg = tmp_path / "repos" / "alpha" / "alpha"
    beta_pkg = tmp_path / "repos" / "beta" / "beta"
    baseline_tests = tmp_path / "baseline"
    (baseline_tests / "alpha").mkdir(parents=True)
    (baseline_tests / "beta").mkdir(parents=True)
    (baseline_tests / "alpha" / "test_alpha.py").write_text("def test_alpha(): pass\n", encoding="utf-8")
    (baseline_tests / "beta" / "test_beta.py").write_text("def test_beta(): pass\n", encoding="utf-8")
    artifacts_dir = tmp_path / "artifacts"
    coverage_outputs = []

    def fake_run_coverage(**kwargs):
        coverage_outputs.append(kwargs)
        symbol = "first" if kwargs["package_dir"] == alpha_pkg else "Second.method"
        source_file = "alpha/a.py" if symbol == "first" else "beta/b.py"
        kwargs["output"].write_text(
            json.dumps(
                {
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
                }
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stdout="coverage ok")

    monkeypatch.setattr("src.optimization.runner.run_coverage", fake_run_coverage)
    monkeypatch.setattr(
        "src.optimization.runner.run_streamed",
        lambda *args, **kwargs: pytest.fail("CoverUp must not be invoked"),
    )
    runner = CoverUpExperimentRunner(
        ExperimentConfig(
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
        )
    )
    targets = [
        SymbolTarget("alpha", "alpha/a.py", "first", "validation"),
        SymbolTarget("beta", "beta/b.py", "Second.method", "validation"),
    ]

    record = runner.evaluate_existing_tests_batch(targets, baseline_tests, split="validation")

    assert len(coverage_outputs) == 2
    assert {str(kwargs["tests_dir"].resolve()) for kwargs in coverage_outputs} == {
        str(baseline_tests.resolve() / "alpha"),
        str(baseline_tests.resolve() / "beta"),
    }
    assert all(result.score["score"] == pytest.approx(0.5) for result in record.results)


def test_resolve_project_layouts_supports_single_project(tmp_path):
    repos = tmp_path / "src" / "sample_repo"
    (repos / "isort" / "isort").mkdir(parents=True)
    targets = [SymbolTarget("isort", "isort/a.py", "f", "train")]
    layouts = _resolve_project_layouts(tmp_path, targets, Path("src/sample_repo"))
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

    layouts = _resolve_project_layouts(tmp_path, targets, Path("src/sample_repo"))

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


def test_resolve_project_layouts_accepts_uploaded_project_manifest(tmp_path):
    source = tmp_path / "workspace" / "src" / "actual_package"
    tests = tmp_path / "workspace" / "project_tests"
    source.mkdir(parents=True)
    tests.mkdir(parents=True)
    manifest = tmp_path / "project-layouts.json"
    manifest.write_text(
        json.dumps(
            {
                "friendly-project-slug": {
                    "package_dir": str(source),
                    "tests_dir": str(tests),
                    "import_root": str(source.parent),
                }
            }
        ),
        encoding="utf-8",
    )

    layouts = _resolve_project_layouts(
        tmp_path,
        [SymbolTarget("friendly-project-slug", "module.py", "work", "train")],
        Path("unused"),
        manifest,
    )

    assert layouts["friendly-project-slug"].package_dir == source
    assert layouts["friendly-project-slug"].tests_dir == tests
    assert layouts["friendly-project-slug"].import_root == source.parent


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
        runner,
        batch_targets,
        bundle,
        candidate_dir,
        *,
        split,
        workspace_kind,
        replicates=1,
        reference_results=None,
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
        runner,
        batch_targets,
        bundle,
        candidate_dir,
        *,
        split,
        workspace_kind,
        replicates=1,
        reference_results=None,
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
