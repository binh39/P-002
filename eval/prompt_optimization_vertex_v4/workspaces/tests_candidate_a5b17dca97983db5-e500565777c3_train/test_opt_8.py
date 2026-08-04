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
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        order_by_type=True,
    )
    res1 = section_key("from .module import foo", config1)
    assert "B. module import foo" == res1

    # 2. Test group_by_package and line starting with "from"
    config2 = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=True,
        lexicographical=False,
        length_sort=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        order_by_type=True,
    )
    res2 = section_key("from module import foo", config2)
    assert res2 == "Bmodule"

    # 3. Test lexicographical=True
    config3 = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=True,
        length_sort=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        order_by_type=True,
    )
    res3 = section_key("import os", config3)
    assert res3.startswith("B")

    # 4. Test sort_relative_in_force_sorted_sections with reverse_relative=True and False
    config4_true = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=True,
        group_by_package=False,
        lexicographical=False,
        length_sort=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        order_by_type=True,
    )
    res4_t = section_key("from .module import foo", config4_true)
    assert "._" not in res4_t

    config4_false = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=False,
        length_sort=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        order_by_type=True,
    )
    res4_f = section_key("from .module import foo", config4_false)
    assert "._" in res4_f

    # 5. Test force_to_top -> section = "A"
    config5 = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=False,
        length_sort=False,
        force_to_top=("os",),
        honor_case_in_force_sorted_sections=False,
        order_by_type=True,
    )
    res5 = section_key("import os", config5)
    assert res5.startswith("A")

    # 6. Test length_sort = True
    config6 = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=False,
        length_sort=True,
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        order_by_type=True,
    )
    res6 = section_key("import os", config6)
    assert res6.startswith("B2")

    # 7. Test honor_case_in_force_sorted_sections and case_sensitive != order_by_type
    # Subcase A: split_module > 1, case_sensitive=False, order_by_type=True
    config7a = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=False,
        length_sort=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res7a = section_key("ModuleA import NamesB", config7a)
    assert "modulea import NamesB" in res7a

    # Subcase B: split_module > 1, case_sensitive=True, order_by_type=False
    config7b = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=False,
        length_sort=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
    )
    res7b = section_key("ModuleA import NamesB", config7b)
    assert "ModuleA import namesb" in res7b

    # Subcase C: len(split_module) <= 1 and not config.case_sensitive
    config7c = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=False,
        length_sort=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res7c = section_key("ModuleA", config7c)
    assert res7c == "Bmodulea"

    # 8. Test elif not config.order_by_type (when honor_case is False or case_sensitive == order_by_type)
    config8 = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=False,
        length_sort=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        case_sensitive=True,
        order_by_type=False,
    )
    res8 = section_key("ModuleA", config8)
    assert res8 == "Bmodulea"
