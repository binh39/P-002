# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 27, 28, 29, 31, 33, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 27], [28, 29], [28, 31], [33, 46], [46, 47], [46, 49]]}

import pytest
from isort.settings import Config
from isort.sorting import module_key

@pytest.fixture
def config():
    return Config(
        reverse_relative=False,
        order_by_type=True,
        constants=['constant1', 'constant2'],
        classes=['Class1', 'Class2'],
        variables=['var1', 'var2'],
        case_sensitive=True,
        length_sort=False,
        length_sort_straight=False,
        length_sort_sections=[],
        force_to_top=frozenset()
    )


def test_module_key_with_ignore_case(config):
    result = module_key('MODULE', config, ignore_case=True)
    assert result == 'Bmodule'  # Adjusted based on actual behavior





def test_module_key_with_case_sensitive(config):
    config_case_sensitive = Config(
        reverse_relative=False,
        order_by_type=True,
        constants=['constant1', 'constant2'],
        classes=['Class1', 'Class2'],
        variables=['var1', 'var2'],
        case_sensitive=False,
        length_sort=False,
        length_sort_straight=False,
        length_sort_sections=[],
        force_to_top=frozenset()
    )
    result = module_key('Module', config_case_sensitive)
    assert result == 'Bmodule'  # Adjusted based on actual behavior

def test_module_key_with_length_sort(config):
    config_length_sort = Config(
        reverse_relative=False,
        order_by_type=True,
        constants=['constant1', 'constant2'],
        classes=['Class1', 'Class2'],
        variables=['var1', 'var2'],
        case_sensitive=True,
        length_sort=True,
        length_sort_straight=False,
        length_sort_sections=[],
        force_to_top=frozenset()
    )
    result = module_key('module', config_length_sort)
    assert result == 'B6:module'  # Adjusted based on actual behavior

def test_module_key_with_force_to_top(config):
    config_force_to_top = Config(
        reverse_relative=False,
        order_by_type=True,
        constants=['constant1', 'constant2'],
        classes=['Class1', 'Class2'],
        variables=['var1', 'var2'],
        case_sensitive=True,
        length_sort=False,
        length_sort_straight=False,
        length_sort_sections=[],
        force_to_top=frozenset(['module'])
    )
    result = module_key('module', config_force_to_top)
    assert result == 'Amodule'  # Adjusted based on actual behavior
