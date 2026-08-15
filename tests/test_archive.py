import json
from pathlib import Path

import pytest

from src.optimization.archive import (
    _load_evaluation_cohort,
    build_candidate_test_archive,
    collect_archive_candidates,
    select_greedy_archive,
    select_sequential_archive_batches,
)
from src.optimization.cli import parser


def _unit(kind, value):
    return (("repo", "repo/mod.py", "target", "validation"), kind, value)


def test_main_cli_exposes_split_locked_archive_command():
    args = parser().parse_args([
        "--repeat-tests",
        "5",
        "archive",
        "--output-dir",
        "archive-output",
        "--split",
        "validation",
    ])

    assert args.command == "archive"
    assert args.repeat_tests == 5
    assert args.allow_holdout is False
    assert args.source_replicates is None


def test_main_cli_accepts_repeated_source_replicates():
    args = parser().parse_args([
        "archive",
        "--output-dir",
        "archive-output",
        "--source-replicate",
        "0",
        "--source-replicate",
        "2",
    ])

    assert args.source_replicates == [0, 2]


def test_main_cli_accepts_ordered_sequential_archive_stages():
    args = parser().parse_args([
        "sequential-archive",
        "--output-dir",
        "archive-output",
        "--stage",
        "baseline:0",
        "--stage",
        "proposal:1",
        "--target-stop-score",
        "0.95",
    ])

    assert args.command == "sequential-archive"
    assert args.stages == [("baseline", 0), ("proposal", 1)]
    assert args.target_stop_score == 0.95


def test_main_cli_defaults_sequential_stop_score_to_calibrated_knee():
    args = parser().parse_args([
        "sequential-archive",
        "--output-dir",
        "archive-output",
        "--stage",
        "baseline:0",
    ])

    assert args.target_stop_score == 0.80


def test_greedy_archive_prefers_one_test_covering_the_union():
    candidates = [
        {
            "id": "a",
            "size_bytes": 10,
            "units": {_unit("statement", 1), _unit("branch", (1, 2))},
        },
        {
            "id": "b",
            "size_bytes": 10,
            "units": {_unit("statement", 2), _unit("branch", (1, 3))},
        },
        {
            "id": "union",
            "size_bytes": 30,
            "units": {
                _unit("statement", 1),
                _unit("statement", 2),
                _unit("branch", (1, 2)),
                _unit("branch", (1, 3)),
            },
        },
    ]
    denominators = {
        ("repo", "repo/mod.py", "target", "validation"): (2, 2)
    }

    selected, covered = select_greedy_archive(candidates, denominators)

    assert [item["id"] for item in selected] == ["union"]
    assert len(covered) == 4


def test_greedy_archive_uses_branch_weight_before_file_size():
    candidates = [
        {
            "id": "statements",
            "size_bytes": 1,
            "units": {_unit("statement", 1), _unit("statement", 2)},
        },
        {
            "id": "branch",
            "size_bytes": 100,
            "units": {_unit("branch", (1, 2))},
        },
    ]
    denominators = {
        ("repo", "repo/mod.py", "target", "validation"): (2, 2)
    }

    selected, _ = select_greedy_archive(candidates, denominators)

    assert selected[0]["id"] == "branch"


def test_archive_keeps_holdout_locked_by_default(tmp_path):
    with pytest.raises(ValueError, match="test split is locked"):
        build_candidate_test_archive(
            project_root=tmp_path,
            artifacts_dir=tmp_path / "artifacts",
            output_dir=tmp_path / "archive",
            sample_repos_dir=Path("src/sample_repo"),
            split="test",
        )


def test_archive_requires_repeated_verification(tmp_path):
    with pytest.raises(ValueError, match="repeat_tests >= 1"):
        build_candidate_test_archive(
            project_root=tmp_path,
            artifacts_dir=tmp_path / "artifacts",
            output_dir=tmp_path / "archive",
            sample_repos_dir=Path("src/sample_repo"),
            repeat_tests=0,
        )


def test_archive_rejects_negative_source_replicate(tmp_path):
    with pytest.raises(ValueError, match="non-negative integers"):
        build_candidate_test_archive(
            project_root=tmp_path,
            artifacts_dir=tmp_path / "artifacts",
            output_dir=tmp_path / "archive",
            sample_repos_dir=Path("src/sample_repo"),
            source_replicates={-1},
        )


def test_archive_content_deduplicates_and_unions_coverage_units(tmp_path):
    source = tmp_path / "test_generated.py"
    source.write_text("def test_generated(): pass\n", encoding="utf-8")
    target = {
        "project": "repo",
        "source_file": "repo/mod.py",
        "symbol": "target",
        "split": "validation",
    }

    def batch(line, replicate):
        return {
            "prompt_digest": "prompt",
            "evaluation_digest": "evaluation",
            "replicate": replicate,
            "results": [{
                "target": target,
                "coverage": {
                    "valid": True,
                    "num_statements": 2,
                    "num_branches": 0,
                    "gained_lines": [line],
                    "gained_branches": [],
                },
                "attempt_traces": [{
                    "outcome": "coverage_gain_saved",
                    "saved_test": str(source),
                    "gained_lines": [line],
                    "gained_branches": [],
                }],
            }],
        }

    candidates, denominators = collect_archive_candidates(
        tmp_path, [batch(1, 0), batch(2, 1)]
    )

    assert len(candidates) == 1
    assert len(candidates[0]["units"]) == 2
    assert len(candidates[0]["origins"]) == 2
    assert denominators[("repo", "repo/mod.py", "target", "validation")] == (2, 0)


def test_archive_auto_selects_largest_evaluation_cohort(tmp_path):
    root = tmp_path / "candidates" / "evaluations" / "prompt"

    def write_batch(digest, targets):
        path = root / digest / "validation" / "batch.json"
        path.parent.mkdir(parents=True)
        path.write_text(
            json.dumps({
                "evaluation_digest": digest,
                "split": "validation",
                "results": [
                    {
                        "target": {
                            "project": "repo",
                            "source_file": "repo/mod.py",
                            "symbol": symbol,
                            "split": "validation",
                        }
                    }
                    for symbol in targets
                ],
            }),
            encoding="utf-8",
        )

    write_batch("small", ["one"])
    write_batch("large", ["one", "two"])

    digest, batches = _load_evaluation_cohort(tmp_path, split="validation")

    assert digest == "large"
    assert len(batches[0]["results"]) == 2


def test_archive_filters_source_replicates(tmp_path):
    root = tmp_path / "candidates" / "evaluations" / "prompt" / "evaluation"
    target = {
        "project": "repo",
        "source_file": "repo/mod.py",
        "symbol": "target",
        "split": "validation",
    }
    for replicate in range(3):
        path = root / "validation" / f"batch_r{replicate}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({
                "evaluation_digest": "evaluation",
                "split": "validation",
                "replicate": replicate,
                "results": [{"target": target}],
            }),
            encoding="utf-8",
        )

    digest, batches = _load_evaluation_cohort(
        tmp_path,
        split="validation",
        source_replicates={0, 2},
    )

    assert digest == "evaluation"
    assert {batch["replicate"] for batch in batches} == {0, 2}


def test_archive_rejects_missing_source_replicate(tmp_path):
    root = tmp_path / "candidates" / "evaluations" / "prompt" / "evaluation"
    path = root / "validation" / "batch_r0.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({
            "evaluation_digest": "evaluation",
            "split": "validation",
            "replicate": 0,
            "results": [],
        }),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"source replicates \[2\]"):
        _load_evaluation_cohort(
            tmp_path,
            split="validation",
            evaluation_digest="evaluation",
            source_replicates={2},
        )


def test_archive_rejects_partially_missing_source_replicates(tmp_path):
    root = tmp_path / "candidates" / "evaluations" / "prompt" / "evaluation"
    path = root / "validation" / "batch_r0.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({
            "evaluation_digest": "evaluation",
            "split": "validation",
            "replicate": 0,
            "results": [{
                "target": {
                    "project": "repo",
                    "source_file": "repo/mod.py",
                    "symbol": "target",
                    "split": "validation",
                }
            }],
        }),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"missing source replicates \[2\]"):
        _load_evaluation_cohort(
            tmp_path,
            split="validation",
            evaluation_digest="evaluation",
            source_replicates={0, 2},
        )


def test_sequential_archive_only_opens_later_stage_for_coverage_gaps(tmp_path):
    first_test = tmp_path / "test_first.py"
    first_test.write_text("def test_first(): pass\n", encoding="utf-8")
    second_test = tmp_path / "test_second.py"
    second_test.write_text("def test_second(): pass\n", encoding="utf-8")
    targets = [
        {
            "project": "repo",
            "source_file": "repo/mod.py",
            "symbol": symbol,
            "split": "validation",
        }
        for symbol in ("covered", "gap")
    ]

    def result(target, source=None):
        gained_lines = [1] if source is not None else []
        traces = (
            [{
                "outcome": "coverage_gain_saved",
                "saved_test": str(source),
                "gained_lines": gained_lines,
                "gained_branches": [],
            }]
            if source is not None
            else []
        )
        return {
            "target": target,
            "coverage": {
                "valid": True,
                "num_statements": 1,
                "num_branches": 0,
                "gained_lines": gained_lines,
                "gained_branches": [],
            },
            "attempt_traces": traces,
        }

    batches = [
        {
            "prompt_digest": "baseline",
            "evaluation_digest": "evaluation",
            "replicate": 0,
            "results": [result(targets[0], first_test), result(targets[1])],
        },
        {
            "prompt_digest": "proposal",
            "evaluation_digest": "evaluation",
            "replicate": 0,
            "results": [result(targets[0]), result(targets[1], second_test)],
        },
    ]

    selected, policy = select_sequential_archive_batches(
        tmp_path,
        batches,
        stages=[("baseline", 0), ("proposal", 0)],
        target_stop_score=0.98,
    )

    assert len(selected[0]["results"]) == 2
    assert [row["target"]["symbol"] for row in selected[1]["results"]] == ["gap"]
    assert policy["target_generation_calls"] == 3
    assert policy["exhaustive_target_generation_calls"] == 4
    assert policy["cohort_exhaustive_target_generation_calls"] == 4
    assert policy["target_generation_savings"] == 0.25
    assert policy["cohort_target_generation_savings"] == 0.25
    assert policy["estimated_aggregate"]["score"] == 1.0


def test_sequential_archive_rejects_missing_cached_stage(tmp_path):
    with pytest.raises(ValueError, match="Missing cached sequential archive stages"):
        select_sequential_archive_batches(
            tmp_path,
            [{"prompt_digest": "baseline", "replicate": 0}],
            stages=[("proposal", 0)],
            target_stop_score=0.98,
        )


def test_sequential_archive_requires_denominators_for_every_target(tmp_path):
    target = {
        "project": "repo",
        "source_file": "repo/mod.py",
        "split": "validation",
    }
    batch = {
        "prompt_digest": "baseline",
        "replicate": 0,
        "results": [
            {
                "target": {**target, "symbol": "measured"},
                "coverage": {
                    "valid": True,
                    "num_statements": 1,
                    "num_branches": 0,
                    "gained_lines": [],
                    "gained_branches": [],
                },
            },
            {"target": {**target, "symbol": "missing"}, "coverage": None},
        ],
    }

    with pytest.raises(ValueError, match="missing coverage denominators for 1 target"):
        select_sequential_archive_batches(
            tmp_path,
            [batch],
            stages=[("baseline", 0)],
            target_stop_score=0.80,
        )


@pytest.mark.parametrize("target_stop_score", [0.0, 1.01])
def test_sequential_archive_rejects_invalid_stop_score(tmp_path, target_stop_score):
    with pytest.raises(ValueError, match="target_stop_score"):
        select_sequential_archive_batches(
            tmp_path,
            [],
            stages=[("baseline", 0)],
            target_stop_score=target_stop_score,
        )
