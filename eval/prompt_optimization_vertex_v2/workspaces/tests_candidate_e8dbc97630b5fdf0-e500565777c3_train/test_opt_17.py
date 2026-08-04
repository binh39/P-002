# file: src\sample_repo\isort\isort\settings.py:693-712
# asked: {"lines": [693, 694, 695, 696, 698, 699, 700, 701, 703, 704, 705, 706, 707, 708, 710, 712], "branches": [[695, 696], [695, 698], [698, 699], [698, 700], [700, 701], [700, 703], [704, 705], [704, 710], [706, 704], [706, 707]]}
# gained: {"lines": [693, 694, 695, 696, 698, 699, 700, 701, 703, 704, 705, 706, 707, 708, 710, 712], "branches": [[695, 696], [695, 698], [698, 699], [698, 700], [700, 701], [700, 703], [704, 705], [704, 710], [706, 704], [706, 707]]}

from types import SimpleNamespace
import pytest
from isort.exceptions import SortingFunctionDoesNotExist
from isort.settings import Config
from isort import sorting


def test_sorting_function_cached():
    config = Config(sort_order="natural")
    # First access sets _sorting_function
    func1 = config.sorting_function
    assert func1 == sorting.naturally
    # Second access returns cached _sorting_function directly (covers line 695-696)
    func2 = config.sorting_function
    assert func2 is func1


def test_sorting_function_natural():
    config = Config(sort_order="natural")
    assert config.sorting_function == sorting.naturally


def test_sorting_function_native():
    config = Config(sort_order="native")
    assert config.sorting_function == sorted


def test_sorting_function_plugin(monkeypatch):
    mock_plugin = SimpleNamespace(
        name="custom_sort",
        load=lambda: (lambda lst, **kwargs: sorted(lst))
    )
    monkeypatch.setattr("isort.settings.entry_points", lambda group: [mock_plugin])
    
    config = Config(sort_order="custom_sort")
    sort_fn = config.sorting_function
    assert callable(sort_fn)
    test_list = ["b", "a"]
    assert sort_fn(test_list) == ["a", "b"]


def test_sorting_function_does_not_exist(monkeypatch):
    mock_plugin = SimpleNamespace(
        name="other_sort",
        load=lambda: sorted
    )
    monkeypatch.setattr("isort.settings.entry_points", lambda group: [mock_plugin])
    
    config = Config(sort_order="non_existent")
    with pytest.raises(SortingFunctionDoesNotExist) as exc_info:
        _ = config.sorting_function
    
    assert exc_info.value.sort_order == "non_existent"
    assert "natural" in exc_info.value.available_sort_orders
    assert "native" in exc_info.value.available_sort_orders
    assert "other_sort" in exc_info.value.available_sort_orders
