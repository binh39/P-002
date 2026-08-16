import json
from collections import Counter
from pathlib import Path

import pytest

from scripts.build_my_isort_dataset import (
    balanced_stratified_split_names,
    stratified_split_names,
)
from src.optimization.dataset import validate_project_stratification
from src.optimization.dataset_builder import (
    build_dataset,
    collect_project_functions,
    rank_functions,
)
from src.optimization.models import SymbolTarget


def _write_file(root: Path, relative: str, source: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def _symbols(functions) -> list[str]:
    return [info.symbol for info in functions]


@pytest.mark.parametrize(
    ("total", "expected"),
    [
        (24, {"train": 5, "validation": 10, "test": 9}),
        (32, {"train": 6, "validation": 13, "test": 13}),
        (40, {"train": 8, "validation": 16, "test": 16}),
    ],
)
def test_isort_stratified_split_is_deterministic_and_exact(total, expected):
    first = stratified_split_names(total, seed=115)
    second = stratified_split_names(total, seed=115)

    assert first == second
    assert Counter(first) == expected


def test_isort_stratified_split_balances_each_full_difficulty_band():
    assignments = stratified_split_names(40, seed=115, stratum_size=5)

    for start in range(0, 40, 5):
        assert Counter(assignments[start : start + 5]) == {
            "train": 1,
            "validation": 2,
            "test": 2,
        }


def test_isort_balanced_stratification_reduces_split_difficulty_skew():
    branches = [318, 134, 85, 72, 60, 50, 45, 40, 35, 30] * 4
    statements = [value + index % 7 for index, value in enumerate(branches)]

    assignments = balanced_stratified_split_names(
        branches, statements, seed=115, stratum_size=5, trials=500
    )
    means = {
        split: sum(
            value
            for value, assigned in zip(branches, assignments, strict=True)
            if assigned == split
        )
        / assignments.count(split)
        for split in ("train", "validation", "test")
    }

    assert Counter(assignments) == {"train": 8, "validation": 16, "test": 16}
    assert max(means.values()) - min(means.values()) < 5


def test_rank_sorts_by_branch_then_statements_then_lines(tmp_path: Path):
    _write_file(
        tmp_path,
        "proj_a/pkg/a.py",
        """
def six_branches(x):
    if x:
        pass
    if x:
        pass
    if x:
        pass

def four_branches_many_statements(x):
    if x:
        first = 1
    else:
        first = 2
    if x:
        second = 1
    return first + second

def four_branches_fewer_statements(x):
    if x:
        return 1
    if x:
        return 2
    return 0
""",
    )
    functions = collect_project_functions(tmp_path / "proj_a" / "pkg", "proj_a")

    ranked = rank_functions(functions)

    assert _symbols(ranked) == [
        "six_branches",
        "four_branches_many_statements",
        "four_branches_fewer_statements",
    ]
    assert ranked[1].statements > ranked[2].statements


def test_rank_uses_lines_before_identity_tiebreak(tmp_path: Path):
    _write_file(
        tmp_path,
        "proj_a/pkg/mod.py",
        """
def compact(x):
    if x:
        a = 1
    return a

def spread(x):
    if x:
        a = 1

    # a comment that only adds lines

    return a
""",
    )
    functions = collect_project_functions(tmp_path / "proj_a" / "pkg", "proj_a")

    ranked = rank_functions(functions)

    assert _symbols(ranked) == ["spread", "compact"]
    assert ranked[0].statements == ranked[1].statements
    assert ranked[0].lines > ranked[1].lines


def test_rank_breaks_final_tie_by_project_then_file_then_symbol(tmp_path: Path):
    source = """
def identical(x):
    if x:
        return 1
    return 0
"""
    _write_file(tmp_path, "z_proj/pkg/z.py", source)
    _write_file(tmp_path, "a_proj/pkg/a.py", source)
    functions = [
        *collect_project_functions(tmp_path / "z_proj" / "pkg", "z_proj"),
        *collect_project_functions(tmp_path / "a_proj" / "pkg", "a_proj"),
    ]

    ranked = rank_functions(functions)

    assert [(info.project, info.source_file) for info in ranked] == [
        ("a_proj", "a_proj/a.py"),
        ("z_proj", "z_proj/z.py"),
    ]


def test_build_dataset_assigns_splits_in_rank_order(tmp_path: Path):
    _write_file(
        tmp_path,
        "proj/pkg/mod.py",
        """
def f1(x):
    if x:
        return 1

def f2(x):
    if x:
        return 1
    if x:
        return 2

def f3(x):
    if x:
        return 1
    if x:
        return 2
    if x:
        return 3

def f4(x):
    if x:
        return 1
    if x:
        return 2
    if x:
        return 3
    if x:
        return 4
""",
    )

    targets, ranked = build_dataset(
        [("proj", tmp_path / "proj" / "pkg")],
        train_limit=1,
        validation_limit=1,
        test_limit=1,
    )

    assert len(targets) == 3
    assert [row["symbol"] for row in targets] == ["f4", "f3", "f2"]
    assert [row["split"] for row in targets] == ["train", "validation", "test"]
    assert all(set(row) == {"project", "source_file", "symbol", "split"} for row in targets)
    assert len(ranked) == 4


def test_build_dataset_stratifies_every_split_by_project(tmp_path: Path):
    for project in ("alpha", "beta"):
        _write_file(
            tmp_path,
            f"{project}/pkg/mod.py",
            "\n".join(
                f"def f{index}(x):\n    if x:\n        return {index}\n"
                for index in range(1, 5)
            ),
        )

    targets, _ = build_dataset(
        [
            ("alpha", tmp_path / "alpha" / "pkg"),
            ("beta", tmp_path / "beta" / "pkg"),
        ],
        train_limit=2,
        validation_limit=2,
        test_limit=2,
    )

    for split in ("train", "validation", "test"):
        assert {
            row["project"] for row in targets if row["split"] == split
        } == {"alpha", "beta"}
    assert {row["symbol"] for row in targets} == {"f1", "f2", "f3"}


def test_project_stratification_validator_rejects_skewed_splits():
    def targets(split: str, alpha: int, beta: int) -> list[SymbolTarget]:
        return [
            SymbolTarget(project, f"{project}/{index}.py", "target", split)
            for project, count in (("alpha", alpha), ("beta", beta))
            for index in range(count)
        ]

    with pytest.raises(ValueError, match="not stratified by project"):
        validate_project_stratification({
            "train": targets("train", 8, 2),
            "validation": targets("validation", 2, 8),
            "test": targets("test", 5, 5),
        })


def test_build_dataset_raises_when_too_few_functions(tmp_path: Path):
    _write_file(
        tmp_path,
        "proj/pkg/mod.py",
        "def only_one():\n    return 1\n",
    )

    try:
        build_dataset(
            [("proj", tmp_path / "proj" / "pkg")],
            train_limit=2,
            validation_limit=1,
            test_limit=1,
        )
    except ValueError as exc:
        assert "Only 1 functions found but 4 were requested" in str(exc)
    else:
        raise AssertionError("build_dataset should reject an undersized project set")


def test_method_symbols_include_enclosing_class(tmp_path: Path):
    _write_file(
        tmp_path,
        "proj/pkg/mod.py",
        """
class Base:
    def __init__(self):
        pass

    def find(self):
        pass

class Other:
    def __init__(self):
        pass
""",
    )
    functions = collect_project_functions(tmp_path / "proj" / "pkg", "proj")

    assert sorted(info.symbol for info in functions) == [
        "Base.__init__",
        "Base.find",
        "Other.__init__",
    ]


def test_phase1_stratified_dataset_has_balanced_existing_targets():
    dataset = Path("binh/phase1_stratified_24.jsonl")
    rows = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines()]
    identities = {
        (row["project"], row["source_file"], row["symbol"])
        for row in rows
    }

    assert len(rows) == len(identities) == 24
    assert Counter(row["split"] for row in rows) == {
        "train": 8,
        "validation": 12,
        "test": 4,
    }
    assert Counter((row["split"], row["project"]) for row in rows) == {
        (split, project): expected
        for split, expected in (("train", 2), ("validation", 3), ("test", 1))
        for project in ("isort", "mimesis", "mlxtend", "typesystem")
    }

    available = set()
    for project in ("isort", "mimesis", "mlxtend", "typesystem"):
        package_dir = Path("src/sample_repo") / project / project
        available.update(
            (info.project, info.source_file, info.symbol)
            for info in collect_project_functions(package_dir, project)
        )
    assert identities <= available
