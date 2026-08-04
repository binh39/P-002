# file: src\sample_repo\isort\isort\settings.py:693-712
# asked: {"lines": [693, 694, 695, 696, 698, 699, 700, 701, 703, 704, 705, 706, 707, 708, 710, 712], "branches": [[695, 696], [695, 698], [698, 699], [698, 700], [700, 701], [700, 703], [704, 705], [704, 710], [706, 704], [706, 707]]}
# gained: {"lines": [693, 694, 695, 696, 698, 699, 700, 701, 703, 704, 710, 712], "branches": [[695, 696], [695, 698], [698, 699], [698, 700], [700, 701], [700, 703], [704, 710]]}

import pytest
from isort.exceptions import SortingFunctionDoesNotExist
from isort.settings import Config


def test_sorting_function_cached():
    config = Config(sort_order="natural")
    # First access populates cache
    func1 = config.sorting_function
    # Second access uses cache (hits line 695: if self._sorting_function is not None: return self._sorting_function)
    func2 = config.sorting_function
    assert func1 is func2
    assert config._sorting_function is func1


def test_sorting_function_natural():
    config = Config(sort_order="natural")
    # Clear cache if any
    config._sorting_function = None
    func = config.sorting_function
    from isort import sorting
    assert func == sorting.naturally


def test_sorting_function_native():
    config = Config(sort_order="native")
    config._sorting_function = None
    func = config.sorting_function
    assert func == sorted


def test_sorting_function_does_not_exist():
    config = Config(sort_order="nonexistent_sort_order_xyz")
    config._sorting_function = None
    with pytest.raises(SortingFunctionDoesNotExist) as exc_info:
        _ = config.sorting_function
    assert "nonexistent_sort_order_xyz" in str(exc_info.value)
