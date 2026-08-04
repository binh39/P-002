# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [97, 98], [97, 100]]}

import pytest
from isort.sorting import section_key
from isort.settings import Config


def test_section_key_full_coverage():
    # 1. Test reverse_relative and line starting with "from ." (lines 61-64)
    config = Config(reverse_relative=True, sort_relative_in_force_sorted_sections=False)
    key = section_key("from .module import foo", config)
    assert ". module" in key

    # 2. Test group_by_package and line starting with "from" (line 69)
    config = Config(group_by_package=True)
    key = section_key("from os import path", config)
    assert "os" in key
    assert "path" not in key

    # 3. Test lexicographical=True (lines 72-73)
    config = Config(lexicographical=True)
    key = section_key("import os", config)
    assert isinstance(key, str)

    # 4. Test sort_relative_in_force_sorted_sections with reverse_relative=True and False (lines 77-79)
    config1 = Config(sort_relative_in_force_sorted_sections=True, reverse_relative=True)
    key1 = section_key("from .module import foo", config1)
    assert ". " in key1

    config2 = Config(sort_relative_in_force_sorted_sections=True, reverse_relative=False)
    key2 = section_key("from .module import foo", config2)
    assert "._" in key2

    # 5. Test force_to_top (lines 80-81)
    config = Config(force_to_top=["os"])
    key = section_key("import os", config)
    assert key.startswith("A")

    # 6. Test honor_case_in_force_sorted_sections and case_sensitive != order_by_type
    # Sub-case A: len(split_module) > 1, case_sensitive=False, order_by_type=True (lines 88-91, 94)
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    key = section_key("from MyModule import FOO", config)
    assert "mymodule import FOO" in key

    # Sub-case B: len(split_module) > 1, case_sensitive=True, order_by_type=False (lines 88, 92-94)
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
    )
    key = section_key("from MyModule import FOO", config)
    assert "MyModule import foo" in key

    # Sub-case C: len(split_module) <= 1 (no import keyword or plain import), case_sensitive=False (lines 95-96)
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    key = section_key("import MyModule", config)
    assert "mymodule" in key

    # 7. Test elif not config.order_by_type (lines 97-98)
    config = Config(
        honor_case_in_force_sorted_sections=False,
        order_by_type=False,
    )
    key = section_key("import MyModule", config)
    assert "mymodule" in key

    # 8. Test length_sort=True (line 100)
    config = Config(length_sort=True)
    key = section_key("import os", config)
    # length of "os" is 2, so '2' should appear between section prefix and line content
    assert key.startswith("B2")
