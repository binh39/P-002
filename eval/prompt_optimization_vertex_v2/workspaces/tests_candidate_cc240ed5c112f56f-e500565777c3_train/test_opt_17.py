# file: src\sample_repo\isort\isort\settings.py:693-712
# asked: {"lines": [693, 694, 695, 696, 698, 699, 700, 701, 703, 704, 705, 706, 707, 708, 710, 712], "branches": [[695, 696], [695, 698], [698, 699], [698, 700], [700, 701], [700, 703], [704, 705], [704, 710], [706, 704], [706, 707]]}
# gained: {"lines": [693, 694, 695, 696, 698, 699, 700, 701, 703, 704, 705, 706, 707, 708, 710, 712], "branches": [[695, 696], [695, 698], [698, 699], [698, 700], [700, 701], [700, 703], [704, 705], [704, 710], [706, 704], [706, 707]]}

import pytest
from types import SimpleNamespace
from isort.settings import Config
from isort.exceptions import SortingFunctionDoesNotExist
from isort import sorting


def test_sorting_function_natural():
    config = Config(sort_order="natural")
    assert config.sorting_function is sorting.naturally
    # Test property cache hits line 695
    assert config.sorting_function is sorting.naturally


def test_sorting_function_native():
    config = Config(sort_order="native")
    assert config.sorting_function is sorted


def test_sorting_function_plugin(monkeypatch):
    dummy_fn = lambda x: x
    plugin = SimpleNamespace(name="custom_sort", load=lambda: dummy_fn)
    monkeypatch.setattr("isort.settings.entry_points", lambda group: [plugin] if group == "isort.sort_function" else [])

    config = Config(sort_order="custom_sort")
    assert config.sorting_function is dummy_fn


def test_sorting_function_does_not_exist(monkeypatch):
    plugin = SimpleNamespace(name="other_sort", load=lambda: (lambda x: x))
    monkeypatch.setattr("isort.settings.entry_points", lambda group: [plugin] if group == "isort.sort_function" else [])

    config = Config(sort_order="nonexistent_sort")
    with pytest.raises(SortingFunctionDoesNotExist) as exc_info:
        _ = config.sorting_function

    assert "nonexistent_sort" in str(exc_info.value)
    assert "natural" in exc_info.value.available_sort_orders
    assert "native" in exc_info.value.available_sort_orders
    assert "other_sort" in exc_info.value.available_sort_orders
