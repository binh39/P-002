# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 69, 70, 72, 73, 75, 76, 77, 80, 81, 86, 87, 88, 89, 90, 91, 92, 94, 97, 98, 100], "branches": [[61, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [90, 91], [92, 94], [97, 98], [97, 100]]}

import pytest
from isort.settings import Config
from isort.sorting import section_key

@pytest.fixture
def config():
    return Config()


def test_section_key_group_by_package(config):
    mutable_config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=True,
        lexicographical=False,
        force_to_top=frozenset(),
        honor_case_in_force_sorted_sections=False,
        case_sensitive=True,
        order_by_type=True,
        length_sort=False
    )
    line = "from package import something"
    expected = "Bpackage"
    assert section_key(line, mutable_config) == expected

def test_section_key_lexicographical(config):
    mutable_config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=True,
        force_to_top=frozenset(),
        honor_case_in_force_sorted_sections=False,
        case_sensitive=True,
        order_by_type=True,
        length_sort=False
    )
    line = "from package import something"
    expected = "Bpackage.something"
    assert section_key(line, mutable_config) == expected


def test_section_key_force_to_top(config):
    mutable_config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=False,
        force_to_top=frozenset(["module"]),
        honor_case_in_force_sorted_sections=False,
        case_sensitive=True,
        order_by_type=True,
        length_sort=False
    )
    line = "module import something"
    result = section_key(line, mutable_config)
    assert result.startswith("A")

def test_section_key_honor_case_in_force_sorted_sections(config):
    mutable_config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=False,
        force_to_top=frozenset(),
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
        length_sort=False
    )
    line = "Module import something"
    expected = "Bmodule import something"
    assert section_key(line, mutable_config) == expected

def test_section_key_case_sensitive(config):
    mutable_config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=False,
        force_to_top=frozenset(),
        honor_case_in_force_sorted_sections=False,
        case_sensitive=True,
        order_by_type=False,
        length_sort=False
    )
    line = "Module import something"
    expected = "Bmodule import something"
    assert section_key(line, mutable_config) == expected
