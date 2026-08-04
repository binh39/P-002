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
        case_sensitive=True,
    )
    res1 = section_key("from . module", config1)
    assert res1 == "B. module"

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
        case_sensitive=True,
    )
    res2 = section_key("from pkg import name", config2)
    assert res2 == "Bpkg"

    # 3. Test lexicographical = True
    config3 = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=True,
        length_sort=True,
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        order_by_type=True,
        case_sensitive=True,
    )
    res3 = section_key("os", config3)
    # len("os") is 2
    assert res3.startswith("B2")

    # 4. Test sort_relative_in_force_sorted_sections = True (with reverse_relative=True and False)
    config4a = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=True,
        group_by_package=False,
        lexicographical=False,
        length_sort=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        order_by_type=True,
        case_sensitive=True,
    )
    res4a = section_key("..foo import bar", config4a)
    assert ".." in res4a

    config4b = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=False,
        length_sort=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        order_by_type=True,
        case_sensitive=True,
    )
    res4b = section_key("..foo import bar", config4b)
    assert ".." in res4b

    # 5. Test force_to_top matching (section = "A")
    config5 = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=False,
        length_sort=False,
        force_to_top=("os",),
        honor_case_in_force_sorted_sections=False,
        order_by_type=True,
        case_sensitive=True,
    )
    res5 = section_key("os", config5)
    assert res5.startswith("A")

    # 6. Test honor_case_in_force_sorted_sections and case_sensitive != order_by_type
    # Case A: len(split_module) > 1
    config6a = Config(
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
    res6a = section_key("ModuleA import NameA", config6a)
    assert "modulea" in res6a

    config6b = Config(
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
    res6b = section_key("ModuleA import NameA", config6b)
    assert "namea" in res6b

    # Case B: len(split_module) <= 1 and not case_sensitive
    config6c = Config(
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
    res6c = section_key("OS", config6c)
    assert res6c == "Bos"

    # 7. Test elif not config.order_by_type branch
    config7 = Config(
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
    res7 = section_key("OS", config7)
    assert res7 == "Bos"
