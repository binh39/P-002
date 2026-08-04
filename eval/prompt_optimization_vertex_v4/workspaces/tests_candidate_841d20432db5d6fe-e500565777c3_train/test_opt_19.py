# file: src\sample_repo\isort\isort\settings.py:693-712
# asked: {"lines": [693, 694, 695, 696, 698, 699, 700, 701, 703, 704, 705, 706, 707, 708, 710, 712], "branches": [[695, 696], [695, 698], [698, 699], [698, 700], [700, 701], [700, 703], [704, 705], [704, 710], [706, 704], [706, 707]]}
# gained: {"lines": [693, 694, 695, 696, 698, 699, 700, 701, 703, 704, 705, 706, 707, 708, 710, 712], "branches": [[695, 696], [695, 698], [698, 699], [698, 700], [700, 701], [700, 703], [704, 705], [704, 710], [706, 704], [706, 707]]}

import pytest
from types import SimpleNamespace
from isort.settings import Config
from isort.exceptions import SortingFunctionDoesNotExist


def test_sorting_function_cached():
    config = Config(sort_order="natural")
    # First access to populate cache
    func1 = config.sorting_function
    # Second access should hit the `if self._sorting_function is not None:` branch
    func2 = config.sorting_function
    assert func1 is func2


def test_sorting_function_natural():
    config = Config(sort_order="natural")
    config._sorting_function = None
    assert config.sorting_function is not None


def test_sorting_function_native():
    config = Config(sort_order="native")
    config._sorting_function = None
    assert config.sorting_function is sorted


def test_sorting_function_custom_plugin(monkeypatch):
    dummy_sort_fn = lambda x: x
    mock_ep = SimpleNamespace(name="custom_sort", load=lambda: dummy_sort_fn)

    # Mock entry_points to return our custom sort plugin
    def mock_entry_points(group):
        if group == "isort.sort_function":
            return [mock_ep]
        return []

    monkeypatch.setattr("isort.settings.entry_points", mock_entry_points)

    config = Config(sort_order="custom_sort")
    config._sorting_function = None
    assert config.sorting_function is dummy_sort_fn


def test_sorting_function_does_not_exist(monkeypatch):
    mock_ep = SimpleNamespace(name="other_sort", load=lambda: (lambda x: x))

    def mock_entry_points(group):
        if group == "isort.sort_function":
            return [mock_ep]
        return []

    monkeypatch.setattr("isort.settings.entry_points", mock_entry_points)

    config = Config(sort_order="nonexistent")
    config._sorting_function = None

    with pytest.raises(SortingFunctionDoesNotExist) as exc_info:
        _ = config.sorting_function

    assert "nonexistent" in str(exc_info.value)
    assert "natural" in exc_info.value.available_sort_orders
    assert "native" in exc_info.value.available_sort_orders
    assert "other_sort" in exc_info.value.available_sort_orders
