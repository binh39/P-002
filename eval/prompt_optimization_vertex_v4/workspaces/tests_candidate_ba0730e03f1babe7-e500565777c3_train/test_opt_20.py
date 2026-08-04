# file: src\sample_repo\isort\isort\settings.py:693-712
# asked: {"lines": [693, 694, 695, 696, 698, 699, 700, 701, 703, 704, 705, 706, 707, 708, 710, 712], "branches": [[695, 696], [695, 698], [698, 699], [698, 700], [700, 701], [700, 703], [704, 705], [704, 710], [706, 704], [706, 707]]}
# gained: {"lines": [693, 694, 695, 696, 698, 699, 700, 701, 703, 704, 710, 712], "branches": [[695, 696], [695, 698], [698, 699], [698, 700], [700, 701], [700, 703], [704, 710]]}

import pytest
from isort import sorting
from isort.exceptions import SortingFunctionDoesNotExist
from isort.settings import Config


def test_sorting_function_cached():
    config = Config(sort_order="natural")
    # First call sets self._sorting_function
    func1 = config.sorting_function
    assert func1 is sorting.naturally

    # Second call hits self._sorting_function is not None (line 695)
    func2 = config.sorting_function
    assert func2 is sorting.naturally


def test_sorting_function_natural():
    config = Config(sort_order="natural")
    config._sorting_function = None  # reset cache
    func = config.sorting_function
    assert func is sorting.naturally


def test_sorting_function_native():
    config = Config(sort_order="native")
    config._sorting_function = None
    func = config.sorting_function
    assert func is sorted


def test_sorting_function_invalid():
    config = Config(sort_order="non_existent_sort_order_xyz")
    config._sorting_function = None
    with pytest.raises(SortingFunctionDoesNotExist) as exc_info:
        _ = config.sorting_function
    assert "non_existent_sort_order_xyz" in str(exc_info.value)
    assert "natural" in exc_info.value.available_sort_orders
    assert "native" in exc_info.value.available_sort_orders
