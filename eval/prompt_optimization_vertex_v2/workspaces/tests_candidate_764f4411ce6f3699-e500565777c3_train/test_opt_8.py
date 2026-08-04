# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [90, 91], [90, 92], [92, 93], [92, 94], [97, 98], [97, 100]]}

from isort.settings import Config
from isort.sorting import section_key


def test_section_key_branches():
    # 1. Test reverse_relative and startswith("from .") when not sort_relative_in_force_sorted_sections
    config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=True,
        group_by_package=False,
        lexicographical=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        order_by_type=True,
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
    )
    res = section_key("from foo import bar", config)
    assert "foo" in res
    assert "bar" not in res

    # 3. Test lexicographical=True
    config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=True,
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        order_by_type=True,
    )
    res = section_key("import os", config)
    assert res.startswith("B")

    # 4. Test sort_relative_in_force_sorted_sections with reverse_relative=True and False
    config_sort_rel_rev = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=True,
        lexicographical=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        order_by_type=True,
    )
    res1 = section_key("from .foo import bar", config_sort_rel_rev)
    assert ". " in res1

    config_sort_rel_norev = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=False,
        lexicographical=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        order_by_type=True,
    )
    res2 = section_key("from .foo import bar", config_sort_rel_norev)
    assert "._" in res2

    # 5. Test force_to_top (section = "A")
    config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        lexicographical=False,
        force_to_top=("os",),
        honor_case_in_force_sorted_sections=False,
        order_by_type=True,
    )
    res = section_key("import os", config)
    assert res.startswith("A")

    # 6. Test honor_case_in_force_sorted_sections and case_sensitive != order_by_type
    # Case A: len(split_module) > 1
    config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        lexicographical=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res = section_key("ModuleA import NamesB", config)
    assert "modulea" in res
    assert "NamesB" in res

    config2 = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        lexicographical=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
    )
    res2 = section_key("ModuleA import NamesB", config2)
    assert "ModuleA" in res2
    assert "namesb" in res2

    # Case B: len(split_module) <= 1 and not config.case_sensitive
    config3 = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        lexicographical=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=False,
    )
    res3 = section_key("ModuleA", config3)
    assert res3.endswith("modulea")

    # 7. Test elif not config.order_by_type (when honor_case... is False)
    config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        lexicographical=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        case_sensitive=True,
        order_by_type=False,
    )
    res = section_key("ModuleA", config)
    assert res.endswith("modulea")

    # 8. Test length_sort=True
    config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        lexicographical=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        order_by_type=True,
        length_sort=True,
    )
    res = section_key("os", config)
    assert "B2os" in res
