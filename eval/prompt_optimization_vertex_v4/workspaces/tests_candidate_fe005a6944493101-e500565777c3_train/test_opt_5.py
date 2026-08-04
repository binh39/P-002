# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 92], [92, 93], [95, 96], [97, 98], [97, 100]]}

import pytest
from isort.sorting import section_key
from isort.settings import Config


def test_section_key_basic():
    config = Config()
    key = section_key("import os", config)
    assert key.startswith("B")


def test_section_key_reverse_relative():
    config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=True,
    )
    line = "from .module import name"
    key = section_key(line, config)
    assert key


def test_section_key_group_by_package():
    config = Config(group_by_package=True)
    line = "from my_package import a, b"
    key = section_key(line, config)
    assert "import" not in key


def test_section_key_lexicographical():
    config = Config(lexicographical=True)
    line = "import os"
    key = section_key(line, config)
    assert key


def test_section_key_sort_relative_in_force_sorted_sections_with_reverse():
    config = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=True,
    )
    line = "from ..mod import foo"
    key = section_key(line, config)
    assert key


def test_section_key_sort_relative_in_force_sorted_sections_without_reverse():
    config = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=False,
    )
    line = "from ..mod import foo"
    key = section_key(line, config)
    assert key


def test_section_key_force_to_top():
    config = Config(force_to_top=["os"])
    line = "import os"
    key = section_key(line, config)
    assert key.startswith("A")


def test_section_key_honor_case_split_with_different_sensitivity():
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
    )
    line = "os import Name"
    key = section_key(line, config)
    assert key


def test_section_key_honor_case_no_split_with_case_insensitive():
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    line = "OS"
    key = section_key(line, config)
    assert key


def test_section_key_order_by_type_false_fallback():
    config = Config(
        honor_case_in_force_sorted_sections=False,
        order_by_type=False,
    )
    line = "OS import Name"
    key = section_key(line, config)
    assert key


def test_section_key_length_sort():
    config = Config(length_sort=True)
    line = "import os"
    key = section_key(line, config)
    # length of "os" after stripping "import " is 2, so key is 'B2os'
    assert "2" in key
