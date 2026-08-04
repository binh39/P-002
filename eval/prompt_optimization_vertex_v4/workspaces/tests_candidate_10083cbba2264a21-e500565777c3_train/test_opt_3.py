# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [97, 98], [97, 100]]}

from isort.settings import Config
from isort.sorting import section_key


def test_section_key_comprehensive():
    # 1. Test reverse_relative and startswith("from .") when not sort_relative_in_force_sorted_sections
    config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=True,
        group_by_package=False,
        lexicographical=False,
    )
    res = section_key("from .foo import bar", config)
    assert "foo" in res

    # 2. Test group_by_package and line.strip().startswith("from")
    config = Config(
        group_by_package=True,
        lexicographical=False,
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
    )
    res = section_key("from foo import bar, baz", config)
    # group_by_package splits at ' import ', 1 and keeps the module part
    assert "bar" not in res

    # 3. Test lexicographical=True
    config = Config(
        lexicographical=True,
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
    )
    res = section_key("import os", config)
    assert res.startswith("B")

    # 4. Test sort_relative_in_force_sorted_sections=True with reverse_relative=True and False
    config_sort_rel_true_rev = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=True,
        lexicographical=False,
    )
    res1 = section_key("from .foo import bar", config_sort_rel_true_rev)
    assert "." in res1

    config_sort_rel_true_no_rev = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=False,
        lexicographical=False,
    )
    res2 = section_key("from .foo import bar", config_sort_rel_true_no_rev)
    assert "." in res2

    # 5. Test force_to_top triggering section = "A"
    config = Config(
        force_to_top=["foo"],
        lexicographical=False,
        sort_relative_in_force_sorted_sections=False,
    )
    res = section_key("import foo", config)
    assert res.startswith("A")

    # 6. Test honor_case_in_force_sorted_sections and case_sensitive != order_by_type
    # Case A: len(split_module) > 1 (contains ' import ')
    # subcase: case_sensitive=False, order_by_type=True
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
        lexicographical=False,
    )
    res = section_key("import Foo import Bar", config)
    assert "foo import Bar" in res

    # subcase: case_sensitive=True, order_by_type=False
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
        lexicographical=False,
    )
    res = section_key("import Foo import Bar", config)
    assert "Foo import bar" in res

    # Case B: len(split_module) == 1 (no ' import ') and not case_sensitive
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
        lexicographical=False,
    )
    res = section_key("import FooBar", config)
    assert "foobar" in res

    # 7. Test elif not config.order_by_type (when honor_case... is False or case_sensitive == order_by_type)
    config = Config(
        honor_case_in_force_sorted_sections=False,
        order_by_type=False,
        lexicographical=False,
    )
    res = section_key("import FooBar", config)
    assert "foobar" in res

    # 8. Test length_sort=True
    config = Config(
        length_sort=True,
        lexicographical=False,
    )
    res = section_key("import foo", config)
    assert "3" in res  # len("foo") is 3
