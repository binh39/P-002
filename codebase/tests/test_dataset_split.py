from src.modules.experiments.dataset import split_targets


def test_split_is_stable_disjoint_and_complete():
    targets = [f"function-{index}" for index in range(10)]
    first = split_targets(targets)
    second = split_targets(list(reversed(targets)))
    assert first == second
    values = [value for split in first.values() for value in split]
    assert set(values) == set(targets)
    assert len(values) == len(set(values))
    assert all(first[name] for name in ("train", "validation", "test"))


def test_small_dataset_is_baseline_only():
    assert split_targets(["one", "two"]) == {"train": ["two", "one"], "validation": [], "test": []}
