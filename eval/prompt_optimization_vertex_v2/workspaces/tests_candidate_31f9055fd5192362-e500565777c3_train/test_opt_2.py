# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [97, 98], [97, 100]]}

import pytest
from isort.settings import Config
from isort.sorting import section_key


def test_section_key_comprehensive():
    # 1. Test reverse_relative and startswith("from .") when sort_relative_in_force_sorted_sections is False
    config = Config(reverse_relative=True, sort_relative_in_force_sorted_sections=False)
    res = section_key("from ..foo import bar", config)
    assert res.startswith("B")

    # 2. Test group_by_package and line starting with "from"
    config = Config(group_by_package=True)
    res = section_key("from foo import bar, baz", config)
    assert "bar" not in res

    # 3. Test lexicographical=True
    config = Config(lexicographical=True)
    res = section_key("import foo", config)
    assert isinstance(res, str)

    # 4. Test sort_relative_in_force_sorted_sections=True with reverse_relative=True vs False
    config_sort_rel_true_rev = Config(sort_relative_in_force_sorted_sections=True, reverse_relative=True)
    res1 = section_key("from .foo import bar", config_sort_rel_true_rev)
    assert res1.startswith("B")

    config_sort_rel_true_no_rev = Config(sort_relative_in_force_sorted_sections=True, reverse_relative=False)
    res2 = section_key("from .foo import bar", config_sort_rel_true_no_rev)
    assert res2.startswith("B")

    # 5. Test force_to_top triggering section = "A"
    config = Config(force_to_top=["foo"])
    res = section_key("foo import bar", config)
    assert res.startswith("A")

    # 6. Test honor_case_in_force_sorted_sections and case_sensitive != order_by_type
    # Case A: len(split_module) > 1
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False
    )
    res = section_key("Foo import Bar", config)
    # module_name ("Foo") stays Foo because case_sensitive=True, names ("Bar") becomes "bar" because order_by_type=False
    assert "Foo import bar" in res

    config2 = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True
    )
    res2 = section_key("Foo import Bar", config2)
    # module_name ("Foo") becomes "foo", names ("Bar") stays "Bar"
    assert "foo import Bar" in res2

    # Case B: len(split_module) == 1, and not config.case_sensitive
    config3 = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True
    )
    res3 = section_key("FooBar", config3)
    assert res3.endswith("foobar")

    # 7. Test elif not config.order_by_type
    config = Config(
        honor_case_in_force_sorted_sections=False,
        order_by_type=False
    )
    res = section_key("FooBar", config)
    assert res.endswith("foobar")

    # 8. Test length_sort=True
    config = Config(length_sort=True)
    res = section_key("foo", config)
    assert "3foo" in res
