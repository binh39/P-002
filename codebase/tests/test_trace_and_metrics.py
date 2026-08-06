import json

from src.modules.experiments.executor import DockerCoverUpExecutor
from src.modules.experiments.traces import as_jsonl, parse_coverup_log


def test_coverup_log_becomes_jsonl_events():
    log = """---- 2026-01-01T00:00:00 file.py:1-2 ----
{"model":"gemini","messages":[]}
---- 2026-01-01T00:00:01 file.py:1-2 ----
{"choices":[{"message":{"content":"test"}}]}
"""
    events = parse_coverup_log(log)
    assert [event["kind"] for event in events] == ["request", "response"]
    assert [json.loads(line)["segment"] for line in as_jsonl(events).decode().splitlines()] == [
        "file.py:1-2",
        "file.py:1-2",
    ]


def test_target_metrics_are_micro_aggregated():
    report = {
        "files": {
            "pkg/a.py": {
                "functions": {
                    "first": {
                        "summary": {"covered_lines": 2, "num_statements": 4, "covered_branches": 1, "num_branches": 2}
                    },
                    "Thing.second": {
                        "summary": {"covered_lines": 3, "num_statements": 3, "covered_branches": 0, "num_branches": 0}
                    },
                }
            }
        }
    }
    metrics = DockerCoverUpExecutor._target_metrics(report, ["first", "second"])
    statement, branch, score = DockerCoverUpExecutor._aggregate_target_metrics(metrics)
    assert statement == 5 / 7
    assert branch == 0.5
    assert score == 0.4 * (5 / 7) + 0.6 * 0.5
