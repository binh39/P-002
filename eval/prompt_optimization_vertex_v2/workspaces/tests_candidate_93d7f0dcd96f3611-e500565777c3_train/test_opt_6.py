# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [97, 98], [97, 100]]}

import pytest
from isort.settings import Config
from isort.sorting import section_key


def test_section_key_comprehensive():
    # 1. Test reverse_relative and line starts with "from ." with sort_relative_in_force_sorted_sections = False
    config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=True,
        group_by_package=False,
        lexicographical=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        order_by_type=True,
        length_sort=False,
    )
    res = section_key("from .foo import bar", config)
    assert ". foo import bar" in res

    # 2. Test group_by_package and line.strip().startswith("from")
    config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=True,
        lexicographical=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        order_by_type=True,
        length_sort=False,
    )
    res = section_key("from foo import bar", config)
    assert res == "Bfoo"

    # 3. Test lexicographical = True
    config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=True,
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        order_by_type=True,
        length_sort=False,
    )
    res = section_key("import os", config)
    assert isinstance(res, str)

    # 4. Test sort_relative_in_force_sorted_sections = True with reverse_relative = True / False
    config_sort_rel_rev = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=True,
        group_by_package=False,
        lexicographical=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        order_by_type=True,
        length_sort=False,
    )
    res = section_key("from ..foo import bar", config_sort_rel_rev)
    assert ".." in res

    config_sort_rel_no_rev = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        order_by_type=True,
        length_sort=False,
    )
    res2 = section_key("from ..foo import bar", config_sort_rel_no_rev)
    assert ".." in res2

    # 5. Test force_to_top setting (section = "A")
    config_force = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=False,
        force_to_top=("os",),
        honor_case_in_force_sorted_sections=False,
        order_by_type=True,
        length_sort=False,
    )
    res = section_key("import os", config_force)
    assert res.startswith("A")

    # 6. Test honor_case_in_force_sorted_sections and case_sensitive != order_by_type
    # Case A: len(split_module) > 1
    config_honor_1 = Config(
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
    res = section_key("from Foo import Bar", config_honor_1)
    # module_name remains 'Foo', names becomes 'bar'
    assert "Foo import bar" in res

    config_honor_2 = Config(
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
    res = section_key("from Foo import Bar", config_honor_2)
    # module_name becomes 'foo', names remains 'Bar'
    assert "foo import Bar" in res

    # Case B: len(split_module) <= 1 (e.g. "import Foo") and case_sensitive = False
    config_honor_3 = Config(
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
    res = section_key("import Foo", config_honor_3)
    assert "foo" in res

    # 7. Test elif not config.order_by_type (when honor_case_in_force_sorted_sections is False)
    config_order_type = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        case_sensitive=True,
        order_by_type=False,
        length_sort=False,
    )
    res = section_key("import OS", config_order_type)
    assert res == "Bos"

    # 8. Test length_sort = True
    config_length_sort = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        case_sensitive=True,
        order_by_type=True,
        length_sort=True,
    )
    res = section_key("import sys", config_length_sort)
    # Should include length of line in the returned format string
    assert "B3sys" in res
