# file: src\sample_repo\isort\isort\settings.py:693-712
# asked: {"lines": [693, 694, 695, 696, 698, 699, 700, 701, 703, 704, 705, 706, 707, 708, 710, 712], "branches": [[695, 696], [695, 698], [698, 699], [698, 700], [700, 701], [700, 703], [704, 705], [704, 710], [706, 704], [706, 707]]}
# gained: {"lines": [693, 694, 695, 698, 699, 700, 701, 703, 704, 705, 706, 707, 708, 710, 712], "branches": [[695, 698], [698, 699], [698, 700], [700, 701], [700, 703], [704, 705], [704, 710], [706, 707]]}

import pytest
from isort.settings import Config
from isort.exceptions import SortingFunctionDoesNotExist
from isort import sorting  # Importing sorting to access the naturally function
from unittest.mock import patch, MagicMock

@pytest.fixture
def config():
    """Fixture to create a Config instance for testing."""
    return Config()

def test_sorting_function_natural(config):
    """Test the sorting_function property with 'natural' sort order."""
    config_with_sort_order = Config(sort_order="natural")
    result = config_with_sort_order.sorting_function
    assert result == sorting.naturally
    assert config_with_sort_order._sorting_function is result

def test_sorting_function_native(config):
    """Test the sorting_function property with 'native' sort order."""
    config_with_sort_order = Config(sort_order="native")
    result = config_with_sort_order.sorting_function
    assert result == sorted
    assert config_with_sort_order._sorting_function is result

def test_sorting_function_custom_plugin(config):
    """Test the sorting_function property with a custom sorting function."""
    mock_plugin = MagicMock()
    mock_plugin.name = "custom_sort"
    mock_plugin.load.return_value = lambda x: x  # A dummy sorting function

    with patch('isort.settings.entry_points', return_value=[mock_plugin]):
        config_with_sort_order = Config(sort_order="custom_sort")
        result = config_with_sort_order.sorting_function
        assert result is mock_plugin.load()
        assert config_with_sort_order._sorting_function is result

def test_sorting_function_invalid(config):
    """Test the sorting_function property with an invalid sort order."""
    config_with_sort_order = Config(sort_order="invalid_sort")

    with pytest.raises(SortingFunctionDoesNotExist) as excinfo:
        config_with_sort_order.sorting_function

    assert str(excinfo.value) == "Specified sort_order of invalid_sort does not exist. Available sort_orders: natural,native."
