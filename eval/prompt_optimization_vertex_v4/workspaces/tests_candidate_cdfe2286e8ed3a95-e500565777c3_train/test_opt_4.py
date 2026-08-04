# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [97, 98], [97, 100]]}

import pytest
from isort.sorting import section_key
from isort.settings import Config


def test_section_key_full_coverage():
    # 1. Test reverse_relative and line starting with "from ."
    config1 = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=True,
        group_by_package=True,
        lexicographical=False,
        force_to_top=("os",),
        honor_case_in_force_sorted_sections=False,
        case_sensitive=True,
        order_by_type=False,
        length_sort=True,
    )
    res1 = section_key("from .module import func", config1)
    assert res1.startswith("B")

    # 2. Test group_by_package False / line not starting with from, lexicographical=True
    config2 = Config(
        lexicographical=True,
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=True,
        length_sort=False,
    )
    res2 = section_key("import sys", config2)
    assert res2.startswith("B")

    # 3. Test honor_case_in_force_sorted_sections and case_sensitive != order_by_type with import split (> 1 parts)
    config3 = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=False,
        force_to_top=("os",),
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
        length_sort=False,
    )
    # line.split(" import ", 1) will have len > 1, case_sensitive=False -> module_name.lower(), order_by_type=True -> names unchanged
    res3 = section_key("os import Func", config3)
    assert res3.startswith("A")

    # 4. Test honor_case_in_force_sorted_sections and case_sensitive != order_by_type with no " import " (len <= 1), case_sensitive=False
    config4 = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
        length_sort=False,
    )
    res4 = section_key("os", config4)
    assert res4.startswith("B")

    # 5. Test honor_case_in_force_sorted_sections with case_sensitive=True, order_by_type=False (names lowercased, module_name unchanged)
    config5 = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
        length_sort=False,
    )
    res5 = section_key("OS import Func", config5)
    assert res5.startswith("B")
