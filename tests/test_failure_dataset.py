import json
from collections import Counter
from pathlib import Path

from src.optimization.failure_dataset import (
    FAILURE_STRATA,
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
