import json
from pathlib import Path

import pytest

from src.optimization.archive import (
    _load_evaluation_cohort,
    build_candidate_test_archive,
    collect_archive_candidates,
    select_greedy_archive,
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
