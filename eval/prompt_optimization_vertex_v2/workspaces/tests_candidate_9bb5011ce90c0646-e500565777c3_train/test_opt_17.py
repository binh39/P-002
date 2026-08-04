# file: src\sample_repo\isort\isort\settings.py:693-712
# asked: {"lines": [693, 694, 695, 696, 698, 699, 700, 701, 703, 704, 705, 706, 707, 708, 710, 712], "branches": [[695, 696], [695, 698], [698, 699], [698, 700], [700, 701], [700, 703], [704, 705], [704, 710], [706, 704], [706, 707]]}
# gained: {"lines": [693, 694, 695, 696, 698, 699, 700, 701, 703, 704, 705, 706, 707, 708, 710, 712], "branches": [[695, 696], [695, 698], [698, 699], [698, 700], [700, 701], [700, 703], [704, 705], [704, 710], [706, 704], [706, 707]]}

from unittest.mock import MagicMock, patch
import pytest
from isort import sorting
from isort.exceptions import SortingFunctionDoesNotExist
from isort.settings import Config


def test_sorting_function_cached():
    config = Config(sort_order="natural")
    # First access populates _sorting_function
    func1 = config.sorting_function
    assert func1 == sorting.naturally

    # Second access hits `if self._sorting_function is not None:` branch
    func2 = config.sorting_function
    assert func2 == sorting.naturally


def test_sorting_function_natural():
    config = Config(sort_order="natural")
    # Reset _sorting_function to None to ensure we test the property getter logic fully
    config._sorting_function = None
    assert config.sorting_function == sorting.naturally


def test_sorting_function_native():
    config = Config(sort_order="native")
    config._sorting_function = None
    assert config.sorting_function == sorted


def test_sorting_function_entry_point():
    mock_plugin = MagicMock()
    mock_plugin.name = "custom_sort"
    mock_plugin.load.return_value = lambda x, **kwargs: x

    with patch("isort.settings.entry_points", return_value=[mock_plugin]):
        config = Config(sort_order="custom_sort")
        config._sorting_function = None
        assert config.sorting_function == mock_plugin.load.return_value
        mock_plugin.load.assert_called_once()


def test_sorting_function_does_not_exist():
    mock_plugin = MagicMock()
    mock_plugin.name = "other_sort"

    with patch("isort.settings.entry_points", return_value=[mock_plugin]):
        config = Config(sort_order="nonexistent")
        config._sorting_function = None
        with pytest.raises(SortingFunctionDoesNotExist) as exc_info:
            _ = config.sorting_function
        
        assert "nonexistent" in str(exc_info.value)
        assert "natural" in exc_info.value.available_sort_orders
        assert "native" in exc_info.value.available_sort_orders
        assert "other_sort" in exc_info.value.available_sort_orders
