# file: src\sample_repo\isort\isort\settings.py:693-712
# asked: {"lines": [693, 694, 695, 696, 698, 699, 700, 701, 703, 704, 705, 706, 707, 708, 710, 712], "branches": [[695, 696], [695, 698], [698, 699], [698, 700], [700, 701], [700, 703], [704, 705], [704, 710], [706, 704], [706, 707]]}
# gained: {"lines": [693, 694, 695, 696, 698, 699, 700, 701, 703, 704, 705, 706, 707, 708, 710, 712], "branches": [[695, 696], [695, 698], [698, 699], [698, 700], [700, 701], [700, 703], [704, 705], [704, 710], [706, 704], [706, 707]]}

import pytest
from unittest.mock import MagicMock, patch
from isort.settings import Config
from isort.exceptions import SortingFunctionDoesNotExist


def test_sorting_function_cached():
    config = Config(sort_order="natural")
    # First access to populate self._sorting_function
    func1 = config.sorting_function
    # Second access to hit lines 695-696 (returning cached function)
    func2 = config.sorting_function
    assert func1 is func2


def test_sorting_function_natural():
    config = Config(sort_order="natural")
    config._sorting_function = None
    func = config.sorting_function
    from isort import sorting
    assert func == sorting.naturally


def test_sorting_function_native():
    config = Config(sort_order="native")
    config._sorting_function = None
    func = config.sorting_function
    assert func == sorted


def test_sorting_function_plugin_found():
    config = Config(sort_order="custom_sort")
    config._sorting_function = None

    mock_plugin = MagicMock()
    mock_plugin.name = "custom_sort"
    expected_func = lambda x: x
    mock_plugin.load.return_value = expected_func

    with patch("isort.settings.entry_points", return_value=[mock_plugin]):
        func = config.sorting_function
        assert func == expected_func


def test_sorting_function_plugin_not_found():
    config = Config(sort_order="nonexistent_sort")
    config._sorting_function = None

    mock_plugin = MagicMock()
    mock_plugin.name = "other_sort"

    with patch("isort.settings.entry_points", return_value=[mock_plugin]):
        with pytest.raises(SortingFunctionDoesNotExist) as exc_info:
            _ = config.sorting_function
        assert "nonexistent_sort" in str(exc_info.value)
        assert "natural" in exc_info.value.available_sort_orders
        assert "native" in exc_info.value.available_sort_orders
        assert "other_sort" in exc_info.value.available_sort_orders
