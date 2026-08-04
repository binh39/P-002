# file: src\sample_repo\isort\isort\settings.py:693-712
# asked: {"lines": [693, 694, 695, 696, 698, 699, 700, 701, 703, 704, 705, 706, 707, 708, 710, 712], "branches": [[695, 696], [695, 698], [698, 699], [698, 700], [700, 701], [700, 703], [704, 705], [704, 710], [706, 704], [706, 707]]}
# gained: {"lines": [693, 694, 695, 698, 699, 700, 701, 712], "branches": [[695, 698], [698, 699], [698, 700], [700, 701]]}

import pytest
from isort.settings import Config
from isort.exceptions import SortingFunctionDoesNotExist
from isort import sorting

class MockEntryPoint:
    def __init__(self, name, load_func):
        self.name = name
        self.load_func = load_func

    def load(self):
        return self.load_func()

def mock_entry_points(group):
    if group == "isort.sort_function":
        return [MockEntryPoint("custom_sort", lambda: lambda x: sorted(x, reverse=True))]
    return []

@pytest.fixture
def config():
    return Config()

def test_sorting_function_natural(config):
    config_instance = Config(sort_order="natural")
    result = config_instance.sorting_function(["b", "a", "c"])
    assert result == ["a", "b", "c"]
    assert config_instance._sorting_function == sorting.naturally

def test_sorting_function_native(config):
    config_instance = Config(sort_order="native")
    result = config_instance.sorting_function(["b", "a", "c"])
    assert result == ["a", "b", "c"]
    assert config_instance._sorting_function.__name__ == "sorted"


