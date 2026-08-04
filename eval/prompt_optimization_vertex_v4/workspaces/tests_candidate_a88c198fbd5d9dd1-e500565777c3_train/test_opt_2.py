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
        group_by_package=False,
        lexicographical=False,
        length_sort=False,
    )
    res1 = section_key("from .module import foo", config1)
    assert res1.startswith("B")

    # 2. Test group_by_package with "from"
    config2 = Config(
        group_by_package=True,
        lexicographical=False,
        length_sort=True,
    )
    res2 = section_key("from os import path", config2)
    assert "os" in res2

    # 3. Test lexicographical=True
    config3 = Config(
        lexicographical=True,
        length_sort=False,
    )
    res3 = section_key("import sys", config3)
    assert res3.startswith("B")

    # 4. Test sort_relative_in_force_sorted_sections with reverse_relative=False and True
    config4_false = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=False,
        length_sort=False,
    )
    res4_false = section_key("from ..foo import bar", config4_false)
    assert res4_false.startswith("B")

    config4_true = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=True,
        length_sort=False,
    )
    res4_true = section_key("from ..foo import bar", config4_true)
    assert res4_true.startswith("B")

    # 5. Test force_to_top matching section A
    config5 = Config(
        force_to_top=("os",),
        length_sort=False,
    )
    res5 = section_key("import os", config5)
    assert res5.startswith("A")

    # 6. Test honor_case_in_force_sorted_sections and case_sensitive != order_by_type
    # case_sensitive=False, order_by_type=True -> with ' import ' (len > 1)
    config6_a = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
        length_sort=False,
    )
    res6_a = section_key("OS import Path", config6_a)
    assert "os import Path" in res6_a

    # case_sensitive=True, order_by_type=False -> with ' import ' (len > 1)
    config6_b = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
        length_sort=False,
    )
    res6_b = section_key("OS import Path", config6_b)
    assert "OS import path" in res6_b

    # case_sensitive=False, order_by_type=False -> with ' import '
    config6_c = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=False,
        length_sort=False,
    )
    res6_c = section_key("OS import Path", config6_c)
    assert "os import path" in res6_c

    # case_sensitive=False, order_by_type=True -> without ' import ' (len == 1)
    config6_d = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
        length_sort=False,
    )
    res6_d = section_key("OSystem", config6_d)
    assert "osystem" in res6_d

    # 7. Test elif not config.order_by_type branch (when honor_case is False, order_by_type=False)
    config7 = Config(
        honor_case_in_force_sorted_sections=False,
        case_sensitive=True,
        order_by_type=False,
        length_sort=False,
    )
    res7 = section_key("OSystem", config7)
    assert "osystem" in res7
