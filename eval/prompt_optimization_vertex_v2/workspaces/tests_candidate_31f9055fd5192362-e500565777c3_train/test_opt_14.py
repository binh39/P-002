# file: src\sample_repo\isort\isort\settings.py:693-712
# asked: {"lines": [693, 694, 695, 696, 698, 699, 700, 701, 703, 704, 705, 706, 707, 708, 710, 712], "branches": [[695, 696], [695, 698], [698, 699], [698, 700], [700, 701], [700, 703], [704, 705], [704, 710], [706, 704], [706, 707]]}
# gained: {"lines": [693, 694, 695, 696, 698, 699, 700, 701, 703, 704, 710, 712], "branches": [[695, 696], [695, 698], [698, 699], [698, 700], [700, 701], [700, 703], [704, 710]]}

import pytest
from isort.exceptions import SortingFunctionDoesNotExist
from isort.settings import Config


def test_sorting_function_cached():
    config = Config(sort_order="natural")
    func1 = config.sorting_function
    func2 = config.sorting_function
    assert func1 is func2


def test_sorting_function_natural():
    config = Config(sort_order="natural")
    sorting_fn = config.sorting_function
    assert sorting_fn(["b", "a"]) == ["a", "b"]


def test_sorting_function_native():
    config = Config(sort_order="native")
    sorting_fn = config.sorting_function
    assert sorting_fn(["b", "a"]) == ["a", "b"]


def test_sorting_function_does_not_exist():
    config = Config(sort_order="nonexistent_sort_order_12345")
    with pytest.raises(SortingFunctionDoesNotExist) as exc_info:
        _ = config.sorting_function
    assert "nonexistent_sort_order_12345" in str(exc_info.value)
    assert "natural" in exc_info.value.available_sort_orders
    assert "native" in exc_info.value.available_sort_orders
