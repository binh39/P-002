# file: src\sample_repo\isort\isort\settings.py:693-712
# asked: {"lines": [693, 694, 695, 696, 698, 699, 700, 701, 703, 704, 705, 706, 707, 708, 710, 712], "branches": [[695, 696], [695, 698], [698, 699], [698, 700], [700, 701], [700, 703], [704, 705], [704, 710], [706, 704], [706, 707]]}
# gained: {"lines": [693, 694, 695, 696, 698, 699, 700, 701, 703, 704, 705, 706, 707, 708, 710, 712], "branches": [[695, 696], [695, 698], [698, 699], [698, 700], [700, 701], [700, 703], [704, 705], [704, 710], [706, 704], [706, 707]]}

from unittest.mock import MagicMock, patch
import pytest

from isort.exceptions import SortingFunctionDoesNotExist
from isort.settings import Config
from isort import sorting


def test_sorting_function_cached():
    config = Config(sort_order="natural")
    # First access sets _sorting_function
    func1 = config.sorting_function
    assert func1 is sorting.naturally

    # Second access returns cached _sorting_function (line 695-696)
    func2 = config.sorting_function
    assert func2 is sorting.naturally


def test_sorting_function_natural():
    config = Config(sort_order="natural")
    assert config.sorting_function is sorting.naturally


def test_sorting_function_native():
    config = Config(sort_order="native")
    assert config.sorting_function is sorted


def test_sorting_function_plugin_found():
    mock_plugin = MagicMock()
    mock_plugin.name = "custom_sort"
    custom_func = lambda x, **kwargs: x
    mock_plugin.load.return_value = custom_func

    with patch("isort.settings.entry_points", return_value=[mock_plugin]):
        config = Config(sort_order="custom_sort")
        assert config.sorting_function is custom_func


def test_sorting_function_does_not_exist():
    mock_plugin = MagicMock()
    mock_plugin.name = "other_sort"

    with patch("isort.settings.entry_points", return_value=[mock_plugin]):
        config = Config(sort_order="nonexistent_sort")
        with pytest.raises(SortingFunctionDoesNotExist) as exc_info:
            _ = config.sorting_function
        
        assert "nonexistent_sort" in str(exc_info.value)
        assert "natural" in exc_info.value.available_sort_orders
        assert "native" in exc_info.value.available_sort_orders
        assert "other_sort" in exc_info.value.available_sort_orders
