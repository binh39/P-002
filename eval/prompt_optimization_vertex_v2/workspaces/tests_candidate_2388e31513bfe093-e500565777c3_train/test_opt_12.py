# file: src\sample_repo\isort\isort\settings.py:693-712
# asked: {"lines": [693, 694, 695, 696, 698, 699, 700, 701, 703, 704, 705, 706, 707, 708, 710, 712], "branches": [[695, 696], [695, 698], [698, 699], [698, 700], [700, 701], [700, 703], [704, 705], [704, 710], [706, 704], [706, 707]]}
# gained: {"lines": [693, 694, 695, 696, 698, 699, 700, 701, 703, 704, 705, 706, 707, 708, 710, 712], "branches": [[695, 696], [695, 698], [698, 699], [698, 700], [700, 701], [700, 703], [704, 705], [704, 710], [706, 704], [706, 707]]}

from types import SimpleNamespace
import pytest
from isort.exceptions import SortingFunctionDoesNotExist
from isort.settings import Config
from isort import sorting


def test_sorting_function_cached(monkeypatch):
    """Test that if self._sorting_function is already set, it is returned immediately."""
    config = Config(sort_order="natural")
    # Pre-set _sorting_function to a sentinel/custom function
    custom_func = lambda *args, **kwargs: ["custom"]
    config._sorting_function = custom_func

    assert config.sorting_function is custom_func


def test_sorting_function_natural():
    """Test that sort_order='natural' returns sorting.naturally."""
    config = Config(sort_order="natural")
    # Reset _sorting_function just in case __init__ populated it
    config._sorting_function = None

    assert config.sorting_function == sorting.naturally


def test_sorting_function_native():
    """Test that sort_order='native' returns built-in sorted."""
    config = Config(sort_order="native")
    config._sorting_function = None

    assert config.sorting_function == sorted


def test_sorting_function_plugin(monkeypatch):
    """Test that a custom sort order provided via entry points is successfully loaded and returned."""
    dummy_load_called = False

    def dummy_load():
        nonlocal dummy_load_called
        dummy_load_called = True
        return sorted

    plugin_mock = SimpleNamespace(name="my_custom_sort", load=dummy_load)

    # Mock entry_points to return our plugin
    monkeypatch.setattr("isort.settings.entry_points", lambda group: [plugin_mock])

    config = Config(sort_order="my_custom_sort")
    config._sorting_function = None

    assert config.sorting_function == sorted
    assert dummy_load_called is True


def test_sorting_function_does_not_exist(monkeypatch):
    """Test that an unknown sort order raises SortingFunctionDoesNotExist with available sort orders."""
    plugin_mock = SimpleNamespace(name="plugin_sort", load=lambda: sorted)
    monkeypatch.setattr("isort.settings.entry_points", lambda group: [plugin_mock])

    config = Config(sort_order="nonexistent_sort")
    config._sorting_function = None

    with pytest.raises(SortingFunctionDoesNotExist) as exc_info:
        _ = config.sorting_function

    assert "nonexistent_sort" in str(exc_info.value)
    # Check that available sort orders include defaults ("natural", "native") and plugin names ("plugin_sort")
    assert "natural" in exc_info.value.available_sort_orders
    assert "native" in exc_info.value.available_sort_orders
    assert "plugin_sort" in exc_info.value.available_sort_orders
