import json
from collections import Counter
from pathlib import Path

import pytest

from src.optimization.failure_dataset import (
    FAILURE_STRATA,
    analyze_observed_failures,
    build_failure_stratified_dataset,
    collect_failure_profiles,
    dataset_digest,
    load_dataset_identities,
)


def _write(root: Path, relative: str, source: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def test_profiles_cover_static_failure_strata(tmp_path: Path):
    _write(
        tmp_path,
        "project/pkg/module.py",
        """
import os

def branch_target(value):
    if value == 1:
        return 1
    if value == 2:
        return 2
    if value == 3:
        return 3
    return 0

def statement_target(value):
    a = value + 1
    b = a + 1
    c = b + 1
    d = c + 1
    e = d + 1
    f = e + 1
    g = f + 1
    h = g + 1
    i = h + 1
    return i

def exception_target(value):
    try:
        assert value
    except AssertionError:
        raise ValueError("missing")
    return value

def dependency_target():
    return os.getenv("PROJECT_VALUE")

async def async_target(stream):
    return await stream.read()

def easy_target():
    return 1

class Stateful:
    def update(self, value):
        self.value = value
        return self.value
""",
    )

    profiles = collect_failure_profiles(tmp_path / "project" / "pkg", "project")
    by_symbol = {profile.info.symbol: set(profile.strata) for profile in profiles}

    assert "branch_heavy" in by_symbol["branch_target"]
    assert "statement_heavy" in by_symbol["statement_target"]
    assert "exception_paths" in by_symbol["exception_target"]
    assert "fixture_mock_dependent" in by_symbol["dependency_target"]
    assert "async_io" in by_symbol["async_target"]
    assert "stateful_method" in by_symbol["Stateful.update"]
    assert by_symbol["easy_target"] == {"easy_regression"}


def test_builder_is_deterministic_balanced_and_excludes_prior_targets(tmp_path: Path):
    projects = []
    for project_index, project in enumerate(("alpha", "beta"), start=1):
        functions = []
        for index in range(1, 9):
            branches = "".join(
                f"    if value == {branch}:\n        return marker + {branch}\n"
                for branch in range(1, index)
            )
            functions.append(
                f"def f{index}(value):\n"
                f"    marker = {project_index * 100 + index}\n"
                f"{branches}"
                "    return marker\n"
            )
        _write(tmp_path, f"{project}/pkg/module.py", "\n".join(functions))
        projects.append((project, tmp_path / project / "pkg"))

    excluded = {("alpha", "alpha/module.py", "f1")}
    first_rows, first_profiles, first_audit = build_failure_stratified_dataset(
        projects,
        train_per_project=1,
        validation_per_project=1,
        test_per_project=1,
        excluded_identities=excluded,
    )
    second_rows, _, second_audit = build_failure_stratified_dataset(
        projects,
        train_per_project=1,
        validation_per_project=1,
        test_per_project=1,
        excluded_identities=excluded,
    )

    assert first_rows == second_rows
    assert first_audit["source_universe_digest"] == second_audit["source_universe_digest"]
    assert len(first_rows) == len(first_profiles) == 6
    assert Counter((row["split"], row["project"]) for row in first_rows) == {
        (split, project): 1
        for split in ("train", "validation", "test")
        for project in ("alpha", "beta")
    }
    assert excluded.isdisjoint(
        (row["project"], row["source_file"], row["symbol"]) for row in first_rows
    )
    assert len({profile.structural_fingerprint for profile in first_profiles}) == 6
    assert dataset_digest(first_rows) == dataset_digest(second_rows)
    for counts in first_audit["difficulty_by_split"].values():
        assert counts["easy"] == 1
        assert sum(counts.values()) == 2
        assert len(counts) == 2


def test_load_dataset_identities_rejects_leakage_input_errors(tmp_path: Path):
    valid = tmp_path / "valid.jsonl"
    valid.write_text(
        json.dumps({
            "project": "project",
            "source_file": "project/module.py",
            "symbol": "target",
            "split": "test",
        })
        + "\n",
        encoding="utf-8",
    )

    assert load_dataset_identities([valid]) == {
        ("project", "project/module.py", "target")
    }
    assert len(FAILURE_STRATA) == 7


def test_e70_benchmark_is_frozen_balanced_and_fresh():
    dataset_path = Path("binh/e70_failure_stratified_32.jsonl")
    manifest_path = Path("binh/e70_failure_stratified_32_manifest.json")
    rows = [
        json.loads(line)
        for line in dataset_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert dataset_digest(rows) == (
        "8876d578f2b65e64ca113fa3e27586fce2be6956ff1e2ff238e4930ffda94fdd"
    )
    assert dataset_digest(rows, "test") == (
        "fa029ed3f1bb2203b28a712d2d67f0c78a03d25d1aaebf2316473fd0879a815c"
    )
    assert manifest["dataset_sha256"] == dataset_digest(rows)
    assert manifest["split_sha256"]["test"] == dataset_digest(rows, "test")
    assert manifest["status"] == "frozen_before_evaluation"
    assert manifest["holdout"]["status"] == "locked_unevaluated"
    assert manifest["model_calls_during_selection"] == 0
    assert manifest["holdout"]["previous_e67_holdout_excluded"] is True

    assert Counter(row["split"] for row in rows) == {
        "train": 16,
        "validation": 8,
        "test": 8,
    }
    assert Counter((row["split"], row["project"]) for row in rows) == {
        (split, project): expected
        for split, expected in (("train", 4), ("validation", 2), ("test", 2))
        for project in ("isort", "mimesis", "mlxtend", "typesystem")
    }
    assert manifest["audit"]["difficulty_by_split"] == {
        "train": {"easy": 4, "hard": 4, "medium": 8},
        "validation": {"easy": 2, "hard": 2, "medium": 4},
        "test": {"easy": 2, "hard": 2, "medium": 4},
    }
    for counts in manifest["audit"]["strata_by_split"].values():
        assert set(FAILURE_STRATA) <= set(counts)

    profiles = manifest["audit"]["profiles"]
    assert len(profiles) == 32
    assert len({profile["structural_fingerprint"] for profile in profiles}) == 32
    identities = {
        (row["project"], row["source_file"], row["symbol"])
        for row in rows
    }
    exclusions = load_dataset_identities([
        Path("binh/phase1_control_12.jsonl"),
        Path("binh/phase1_ablation_16.jsonl"),
        Path("binh/phase1_ablation_16_v2.jsonl"),
        Path("binh/phase1_stratified_24.jsonl"),
    ])
    assert len(identities) == 32
    assert identities.isdisjoint(exclusions)


def test_observed_failure_analysis_joins_profiles_and_rejects_holdout():
    manifest = {
        "dataset_sha256": "dataset",
        "holdout": {"status": "locked_unevaluated"},
        "audit": {
            "profiles": [
                {
                    "project": "alpha",
                    "source_file": "alpha/a.py",
                    "symbol": "easy",
                    "split": "train",
                    "difficulty_band": "easy",
                    "strata": ["easy_regression"],
                },
                {
                    "project": "beta",
                    "source_file": "beta/b.py",
                    "symbol": "hard",
                    "split": "validation",
                    "difficulty_band": "hard",
                    "strata": ["branch_heavy", "statement_heavy"],
                },
                {
                    "project": "gamma",
                    "source_file": "gamma/c.py",
                    "symbol": "locked",
                    "split": "test",
                    "difficulty_band": "medium",
                    "strata": ["exception_paths"],
                },
            ]
        },
    }
    train_result = {
        "target": {
            "project": "alpha",
            "source_file": "alpha/a.py",
            "symbol": "easy",
            "split": "train",
        },
        "score": 1.0,
        "coverage": {
            "score": 1.0,
            "statement_coverage": 1.0,
            "branch_coverage": 1.0,
            "covered_statements": 2,
            "num_statements": 2,
            "covered_branches": 0,
            "num_branches": 0,
        },
        "attempt_traces": [{"attempt": 1, "outcome": "coverage_gain_saved"}],
    }
    validation_result = {
        "target": {
            "project": "beta",
            "source_file": "beta/b.py",
            "symbol": "hard",
            "split": "validation",
        },
        "score": 0.0,
        "coverage": {
            "score": 0.0,
            "statement_coverage": 0.0,
            "branch_coverage": 0.0,
            "covered_statements": 0,
            "num_statements": 8,
            "covered_branches": 0,
            "num_branches": 4,
        },
        "attempt_traces": [
            {
                "attempt": 1,
                "outcome": "test_error",
                "execution_error": "E   AttributeError: missing behavior",
            },
            {"attempt": 1, "outcome": "max_attempts_exhausted"},
        ],
    }
    batches = [
        {
            "split": "train",
            "replicate": 0,
            "evaluation_digest": "train-digest",
            "run_ids": ["train-run"],
            "results": [train_result],
        },
        {
            "split": "validation",
            "replicate": 0,
            "evaluation_digest": "validation-digest",
            "run_ids": ["validation-run"],
            "results": [validation_result],
        },
    ]

    summary = analyze_observed_failures(manifest, batches)

    assert summary["target_count"] == 2
    assert summary["holdout_analyzed"] is False
    assert summary["overall"]["covered_statements"] == 2
    assert summary["overall"]["num_statements"] == 10
    assert summary["headroom"]["zero_score_share_of_statement_headroom"] == 1.0
    assert summary["events"]["attempt_count"] == 2
    assert summary["events"]["failure_types"] == {
        "attribute_error": 1,
        "max_attempts_exhausted": 1,
    }
    assert summary["groups"]["stratum"]["branch_heavy"]["zero_score_count"] == 1

    locked_batch = {
        "split": "test",
        "replicate": 0,
        "run_ids": ["forbidden"],
        "results": [],
    }
    with pytest.raises(ValueError, match="locked split"):
        analyze_observed_failures(manifest, [locked_batch])


def test_e70_baseline_summary_keeps_holdout_locked_and_headroom_stable():
    summary = json.loads(
        Path("binh/e70_baseline_labeling_summary.json").read_text(encoding="utf-8")
    )

    assert summary["dataset_sha256"] == (
        "8876d578f2b65e64ca113fa3e27586fce2be6956ff1e2ff238e4930ffda94fdd"
    )
    assert summary["analyzed_splits"] == ["train", "validation"]
    assert summary["holdout_status"] == "locked_unevaluated"
    assert summary["holdout_analyzed"] is False
    assert summary["target_count"] == 24
    assert summary["overall"]["score"] == pytest.approx(0.3489779384270223)
    assert summary["overall"]["full_score_count"] == 20
    assert summary["overall"]["zero_score_count"] == 2
    assert summary["headroom"]["zero_score_share_of_statement_headroom"] == (
        pytest.approx(0.996415770609319)
    )
    assert summary["headroom"]["zero_score_share_of_branch_headroom"] == (
        pytest.approx(0.9523809523809523)
    )
    assert summary["events"]["attempt_count"] == 35
    assert summary["events"]["terminal_outcomes"] == {
        "coverage_gain_saved": 22,
        "max_attempts_exhausted": 2,
    }
    zero_targets = {
        (target["project"], target["symbol"])
        for target in summary["targets"]
        if target["score"] == 0.0
    }
    assert zero_targets == {
        ("isort", "Config.__init__"),
        ("mlxtend", "SequentialFeatureSelector.fit"),
    }
