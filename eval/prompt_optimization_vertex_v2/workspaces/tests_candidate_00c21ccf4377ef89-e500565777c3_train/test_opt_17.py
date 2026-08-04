# file: src\sample_repo\isort\isort\settings.py:693-712
# asked: {"lines": [693, 694, 695, 696, 698, 699, 700, 701, 703, 704, 705, 706, 707, 708, 710, 712], "branches": [[695, 696], [695, 698], [698, 699], [698, 700], [700, 701], [700, 703], [704, 705], [704, 710], [706, 704], [706, 707]]}
# gained: {"lines": [693, 694, 695, 696, 698, 699, 700, 701, 703, 704, 705, 706, 707, 708, 710, 712], "branches": [[695, 696], [695, 698], [698, 699], [698, 700], [700, 701], [700, 703], [704, 705], [704, 710], [706, 707]]}

import pytest
from isort.exceptions import SortingFunctionDoesNotExist
from isort.settings import Config
from isort import sorting


def test_sorting_function_cached():
    config = Config(sort_order="natural")
    # First access computes and caches
    func1 = config.sorting_function
    assert func1 == sorting.naturally
    # Second access returns cached value (line 695 branch)
    func2 = config.sorting_function
    assert func1 is func2


def test_sorting_function_natural():
    config = Config(sort_order="natural")
    assert config.sorting_function == sorting.naturally


def test_sorting_function_native():
    config = Config(sort_order="native")
    assert config.sorting_function == sorted


def test_sorting_function_plugin(monkeypatch):
    class MockEntryPoint:
        name = "custom_sort"
        def load(self):
            return lambda lst: sorted(lst, reverse=True)

    def mock_entry_points(group=None):
        if group == "isort.sort_function":
            return [MockEntryPoint()]
        return []

    monkeypatch.setattr("isort.settings.entry_points", mock_entry_points)

    config = Config(sort_order="custom_sort")
    sort_func = config.sorting_function
    assert sort_func(["b", "a"]) == ["b", "a"]


def test_sorting_function_does_not_exist(monkeypatch):
    def mock_entry_points(group=None):
        if group == "isort.sort_function":
            return []
        return []

    monkeypatch.setattr("isort.settings.entry_points", mock_entry_points)

    config = Config(sort_order="non_existent")
    with pytest.raises(SortingFunctionDoesNotExist) as exc_info:
        _ = config.sorting_function
    assert "non_existent" in str(exc_info.value)
