# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [97, 98], [97, 100]]}

import pytest
from isort.settings import Config
from isort.sorting import section_key

def test_section_key_comprehensive():
    # 1. Test reverse_relative and startswith("from .") when not sort_relative_in_force_sorted_sections
    config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=True,
    )
    res = section_key("from .module import foo", config)
    assert res.startswith("B")

    # 2. Test group_by_package with import statement starting with from
    config = Config(
        group_by_package=True,
    )
    res = section_key("from os import path", config)
    assert " import " not in res

    # 3. Test lexicographical sorting
    config = Config(
        lexicographical=True,
    )
    res = section_key("import os", config)
    assert isinstance(res, str)

    # 4. Test sort_relative_in_force_sorted_sections with reverse_relative=True and False
    config = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=True,
    )
    res1 = section_key("from ..foo import bar", config)

    config_false_rev = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=False,
    )
    res2 = section_key("from ..foo import bar", config_false_rev)
    assert res1 != res2

    # 5. Test force_to_top triggering section "A"
    config = Config(
        force_to_top=["os"],
    )
    res = section_key("os", config)
    assert res.startswith("A")

    # 6. Test honor_case_in_force_sorted_sections and case_sensitive != order_by_type (with split_module length > 1 and length == 1)
    # Case A: len(split_module) > 1
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res = section_key("ModuleA import NamesB", config)
    assert "modulea" in res

    config2 = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
    )
    res2 = section_key("ModuleA import NamesB", config2)
    assert "namesb" in res2

    # Case B: len(split_module) == 1 (e.g. "import ModuleA" or just "ModuleA" after regex sub)
    config3 = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res3 = section_key("import ModuleA", config3)
    assert res3.endswith("modulea")

    # 7. Test elif not config.order_by_type (when honor_case_in_force_sorted_sections is False)
    config = Config(
        honor_case_in_force_sorted_sections=False,
        case_sensitive=True,
        order_by_type=False,
    )
    res = section_key("import ModuleA", config)
    assert res.endswith("modulea")

    # 8. Test length_sort=True
    config = Config(
        length_sort=True,
    )
    res = section_key("import os", config)
    # Length of modified line should be embedded right after section character 'B'
    assert res[1].isdigit()
