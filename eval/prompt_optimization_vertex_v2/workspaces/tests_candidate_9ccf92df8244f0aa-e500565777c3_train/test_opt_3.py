# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [97, 98], [97, 100]]}

import pytest
from isort.settings import Config
from isort.sorting import section_key


def test_section_key_comprehensive():
    # 1. Test reverse_relative and line starts with "from ."
    # when sort_relative_in_force_sorted_sections is False
    config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=True,
    )
    res = section_key("from .foo import bar", config)
    assert "foo" in res

    # 2. Test group_by_package and line starts with "from"
    config = Config(group_by_package=True)
    res = section_key("from foo import bar", config)
    # line should become just "foo" after split, stripped, etc.
    assert "bar" not in res

    # 3. Test lexicographical=True
    config = Config(lexicographical=True)
    res = section_key("import foo", config)
    assert isinstance(res, str)

    # 4. Test sort_relative_in_force_sorted_sections=True with reverse_relative=True/False
    config_sort_rel_true_rev = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=True,
    )
    res1 = section_key("from .foo import bar", config_sort_rel_true_rev)
    assert res1.startswith("B")

    config_sort_rel_true_no_rev = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=False,
    )
    res2 = section_key("from .foo import bar", config_sort_rel_true_no_rev)
    assert res2.startswith("B")

    # 5. Test force_to_top matching
    config = Config(force_to_top=["my_top_module"])
    res = section_key("import my_top_module", config)
    assert res.startswith("A")

    # 6. Test honor_case_in_force_sorted_sections and case_sensitive != order_by_type
    # case_sensitive = False, order_by_type = True
    config_honor_diff = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    # with split_module > 1 (contains " import ")
    res = section_key("from MyMod import MyName", config_honor_diff)
    assert "mymod" in res
    assert "MyName" in res  # order_by_type is True, so names remain unchanged

    # case_sensitive = True, order_by_type = False
    config_honor_diff2 = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
    )
    res = section_key("from MyMod import MyName", config_honor_diff2)
    assert "MyMod" in res
    assert "myname" in res  # order_by_type is False, so names.lower()

    # without " import " (len(split_module) <= 1), and case_sensitive = False
    config_honor_diff3 = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res = section_key("import MyModuleOnly", config_honor_diff3)
    assert "mymoduleonly" in res

    # 7. Test elif not config.order_by_type (when honor_case_in_force_sorted_sections is False)
    config_no_order_by_type = Config(
        honor_case_in_force_sorted_sections=False,
        case_sensitive=True,
        order_by_type=False,
    )
    res = section_key("import MyModule", config_no_order_by_type)
    assert "mymodule" in res

    # 8. Test length_sort=True
    config_length_sort = Config(length_sort=True)
    res = section_key("import foo", config_length_sort)
    # Should include length in the section key string
    assert str(len("foo")) in res
