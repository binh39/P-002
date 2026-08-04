# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [97, 98], [97, 100]]}

from isort.settings import Config
from isort.sorting import section_key


def test_section_key_comprehensive():
    # 1. Test reverse_relative and line.startswith("from .")
    config1 = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=True,
        group_by_package=False,
        lexicographical=False,
        length_sort=True,
    )
    res1 = section_key("from .module import something", config1)
    assert res1.startswith("B")

    # 2. Test group_by_package and line.strip().startswith("from")
    config2 = Config(
        group_by_package=True,
        lexicographical=False,
        length_sort=False,
    )
    res2 = section_key("from os import path", config2)
    assert "import" not in res2

    # 3. Test lexicographical=True
    config3 = Config(
        lexicographical=True,
        length_sort=False,
    )
    res3 = section_key("import os", config3)
    assert isinstance(res3, str)

    # 4. Test sort_relative_in_force_sorted_sections = True with reverse_relative = True & False
    config4_true = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=True,
        lexicographical=False,
    )
    res4_true = section_key("from .module import foo", config4_true)
    assert ". " in res4_true

    config4_false = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=False,
        lexicographical=False,
    )
    res4_false = section_key("from .module import foo", config4_false)
    assert "._" in res4_false

    # 5. Test force_to_top -> sets section = "A"
    config5 = Config(
        force_to_top=("topmodule",),
        lexicographical=False,
    )
    res5 = section_key("topmodule import something", config5)
    assert res5.startswith("A")

    # 6. Test honor_case_in_force_sorted_sections and case_sensitive != order_by_type
    # With ' import ' in line (len > 1 split)
    config6_a = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
        lexicographical=False,
    )
    res6_a = section_key("ModuleA import NamesB", config6_a)
    assert "namesb" in res6_a

    config6_b = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
        lexicographical=False,
    )
    res6_b = section_key("ModuleA import NamesB", config6_b)
    assert "modulea" in res6_b

    # Without ' import ' in line (len == 1 split), case_sensitive = False
    config6_c = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
        lexicographical=False,
    )
    res6_c = section_key("ModuleA", config6_c)
    assert res6_c.endswith("modulea")

    # 7. Test elif not config.order_by_type (when honor_case... is False)
    config7 = Config(
        honor_case_in_force_sorted_sections=False,
        order_by_type=False,
        lexicographical=False,
    )
    res7 = section_key("ModuleA import NamesB", config7)
    assert res7.endswith("modulea import namesb")
