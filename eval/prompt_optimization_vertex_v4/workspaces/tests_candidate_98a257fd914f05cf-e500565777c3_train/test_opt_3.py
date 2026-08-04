# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [97, 98], [97, 100]]}

import pytest
from isort.settings import Config
from isort.sorting import section_key


def test_section_key_comprehensive():
    # 1. Test lines 61-68: reverse_relative, not sort_relative_in_force_sorted_sections, line starts with "from ."
    config_rev = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=True,
    )
    res = section_key("from .module import foo", config_rev)
    assert res.startswith("B")

    # 2. Test line 69-70: group_by_package and line starts with from
    config_group = Config(group_by_package=True)
    res = section_key("from os import path", config_group)
    assert "import" not in res

    # 3. Test lines 72-73: lexicographical=True
    config_lex = Config(lexicographical=True)
    res = section_key("import os", config_lex)
    assert isinstance(res, str)

    # 4. Test lines 77-79: sort_relative_in_force_sorted_sections=True with reverse_relative=True and False
    config_sort_rel_true = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=True,
    )
    res1 = section_key("from .mod import x", config_sort_rel_true)
    assert "._" not in res1  # Uses space separator because reverse_relative=True

    config_sort_rel_false = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=False,
    )
    res2 = section_key("from .mod import x", config_sort_rel_false)
    assert "._" in res2

    # 5. Test line 80: force_to_top sets section to "A"
    config_force = Config(force_to_top=["os"])
    res = section_key("import os", config_force)
    assert res.startswith("A")

    # 6. Test lines 86-94: honor_case_in_force_sorted_sections and case_sensitive != order_by_type (with ' import ')
    config_honor_1 = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res = section_key("OS import FOO", config_honor_1)
    assert "os import FOO" in res

    config_honor_2 = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
    )
    res = section_key("OS import FOO", config_honor_2)
    assert "OS import foo" in res

    # 7. Test lines 95-96: honor_case_in_force_sorted_sections, case_sensitive != order_by_type, no ' import '
    config_honor_no_import = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res = section_key("OSMODULE", config_honor_no_import)
    assert res.endswith("osmodule")

    # 8. Test lines 97-98: elif not config.order_by_type (when honor_case is False or case_sensitive == order_by_type)
    config_order = Config(
        honor_case_in_force_sorted_sections=False,
        order_by_type=False,
    )
    res = section_key("IMPORT OS", config_order)
    assert res.endswith("os")

    # 9. Test line 100 length_sort option
    config_length = Config(length_sort=True)
    res = section_key("import os", config_length)
    # Should contain the length number between section and line
    assert res[1].isdigit()
