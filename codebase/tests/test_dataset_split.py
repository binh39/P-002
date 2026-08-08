from src.modules.experiments.dataset import select_targets, split_targets
from src.modules.experiments.schemas import DatasetPercentages, SamplingMethod, TargetReference


def target(index: int) -> TargetReference:
    return TargetReference(
        project_id="project",
        function_id=f"function-{index}",
        project="project",
        source_file="pkg/module.py",
        symbol=f"function_{index}",
    )


def test_split_is_stable_disjoint_complete_and_uses_percentages():
    targets = [target(index) for index in range(10)]
    percentages = DatasetPercentages(train=50, validation=30, test=20)
    first = split_targets(targets, percentages, seed=19)
    second = split_targets(list(reversed(targets)), percentages, seed=19)
    assert first == second
    assert {name: len(values) for name, values in first.items()} == {"train": 5, "validation": 3, "test": 2}
    values = [value for split in first.values() for value in split]
    assert set(values) == {item.key for item in targets}
    assert len(values) == len(set(values))


def test_default_percentages_are_twenty_forty_forty():
    assert DatasetPercentages().model_dump() == {"train": 20, "validation": 40, "test": 40}


def test_random_seed_changes_the_snapshot():
    targets = [target(index) for index in range(12)]
    assert split_targets(targets, DatasetPercentages(), seed=1) != split_targets(targets, DatasetPercentages(), seed=2)


def test_selection_has_no_implicit_fifty_target_cap():
    targets = [target(index) for index in range(80)]
    assert len(select_targets(targets, SamplingMethod.RANDOM, seed=7)) == 80
    assert len(select_targets(targets, SamplingMethod.MOST_BRANCHES, seed=7, max_targets=65)) == 65
