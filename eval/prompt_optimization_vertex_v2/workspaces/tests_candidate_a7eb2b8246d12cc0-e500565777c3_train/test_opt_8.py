# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [97, 98], [97, 100]]}

from isort.settings import Config
from isort.sorting import section_key


def test_section_key_branches():
    # 1. Test reverse_relative and startswith("from .") when not sort_relative_in_force_sorted_sections
    config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=True,
    )
    res = section_key("from .foo import bar", config)
    assert ". foo import bar" in res

    # 2. Test group_by_package and line starting with "from"
    config = Config(group_by_package=True)
    res = section_key("from foo import bar, baz", config)
    assert res == "Bfoo"

    # 3. Test lexicographical=True
    config = Config(lexicographical=True)
    res = section_key("import os", config)
    assert isinstance(res, str)

    # 4. Test sort_relative_in_force_sorted_sections=True with reverse_relative=True and False
    config = Config(sort_relative_in_force_sorted_sections=True, reverse_relative=True)
    res = section_key("from ..foo import bar", config)
    assert res.startswith("B")

    config2 = Config(sort_relative_in_force_sorted_sections=True, reverse_relative=False)
    res2 = section_key("from ..foo import bar", config2)
    assert res2.startswith("B")

    # 5. Test force_to_top matching
    config = Config(force_to_top=["os"])
    res = section_key("import os", config)
    assert res.startswith("A")

    # 6. Test honor_case_in_force_sorted_sections and case_sensitive != order_by_type
    # Case A: len(split_module) > 1
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
    )
    res = section_key("from ModuleA import NameA", config)
    # order_by_type is False -> names.lower(), case_sensitive is True -> module_name preserved
    assert "ModuleA import namea" in res

    config_case_false = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res = section_key("from ModuleA import NameA", config_case_false)
    # case_sensitive is False -> module_name.lower(), order_by_type is True -> names preserved
    assert "modulea import NameA" in res

    # Case B: len(split_module) <= 1 (e.g. just a line without ' import ')
    # and case_sensitive = False
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res = section_key("ModuleA", config)
    assert res == "Bmodulea"

    # 7. Test elif not config.order_by_type (when honor_case... is False or case_sensitive == order_by_type)
    config = Config(
        honor_case_in_force_sorted_sections=False,
        order_by_type=False,
    )
    res = section_key("import ModuleA", config)
    assert res == "Bmodulea"

    # 8. Test length_sort=True
    config = Config(length_sort=True)
    res = section_key("import sys", config)
    assert "3" in res  # len("sys") is 3
