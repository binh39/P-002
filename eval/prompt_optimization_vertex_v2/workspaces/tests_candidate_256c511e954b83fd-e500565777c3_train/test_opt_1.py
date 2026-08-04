# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [97, 98], [97, 100]]}

import pytest
from isort.settings import Config
from isort.sorting import section_key


def test_section_key_comprehensive():
    # 1. Test reverse_relative and startswith "from ."
    # covers lines 61-64, 66-68
    config_rev = Config(reverse_relative=True, sort_relative_in_force_sorted_sections=False)
    res = section_key("from .module import name", config_rev)
    assert "module" in res

    # 2. Test group_by_package and line.strip().startswith("from")
    # covers line 69-70
    config_group = Config(group_by_package=True)
    res = section_key("from os import path", config_group)
    assert "import" not in res

    # 3. Test lexicographical=True
    # covers line 72-73
    config_lex = Config(lexicographical=True)
    res = section_key("import os", config_lex)
    assert isinstance(res, str)

    # 4. Test sort_relative_in_force_sorted_sections with reverse_relative=True and False
    # covers lines 77-79 with both sep branches
    config_force_rev = Config(sort_relative_in_force_sorted_sections=True, reverse_relative=True)
    res1 = section_key("from .module import name", config_force_rev)

    config_force_nor = Config(sort_relative_in_force_sorted_sections=True, reverse_relative=False)
    res2 = section_key("from .module import name", config_force_nor)
    assert res1 != res2

    # 5. Test force_to_top
    # covers lines 80-81
    config_top = Config(force_to_top=["os"])
    res = section_key("import os", config_top)
    assert res.startswith("A")

    # 6. Test honor_case_in_force_sorted_sections and case_sensitive != order_by_type
    # Subcase A: split_module len > 1, case_sensitive=False, order_by_type=True
    # covers lines 86-94 (module_name lowered, names not lowered)
    config_honor_1 = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res = section_key("OS import Path", config_honor_1)
    assert "os import Path" in res

    # Subcase B: split_module len > 1, case_sensitive=True, order_by_type=False
    # covers lines 86-94 (module_name not lowered, names lowered)
    config_honor_2 = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
    )
    res = section_key("OS import Path", config_honor_2)
    assert "OS import path" in res

    # Subcase C: split_module len <= 1 (no import keyword), case_sensitive=False
    # covers lines 86-96 (line.lower())
    config_honor_3 = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res = section_key("OSModule", config_honor_3)
    assert "osmodule" in res

    # 7. Test elif not config.order_by_type
    # covers lines 97-98
    config_order = Config(
        honor_case_in_force_sorted_sections=False,
        order_by_type=False,
    )
    res = section_key("OSModule IMPORT Name", config_order)
    assert res == "Bosmodule import name"

    # 8. Test length_sort
    # covers line 100 length_sort branch
    config_len = Config(length_sort=True)
    res = section_key("sys", config_len)
    assert "3sys" in res
