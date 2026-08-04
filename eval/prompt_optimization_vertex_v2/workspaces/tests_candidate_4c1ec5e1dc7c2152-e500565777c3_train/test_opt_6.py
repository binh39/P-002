# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [97, 98], [97, 100]]}

from isort.settings import Config
from isort.sorting import section_key


def test_section_key_all_branches():
    # 1. Test lines 61-68: reverse_relative=True, sort_relative_in_force_sorted_sections=False, line starts with "from ."
    config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=True,
    )
    res = section_key("from .module import name", config)
    assert ". module" in res

    # 2. Test lines 69-70: group_by_package=True and line starts with "from"
    config = Config(group_by_package=True)
    res = section_key("from os import path", config)
    # group_by_package splits on " import ", leaving just the module part ("os")
    assert "os" in res

    # 3. Test lines 72-73: lexicographical=True
    config = Config(lexicographical=True)
    res = section_key("import os", config)
    assert isinstance(res, str)

    # 4. Test lines 77-79: sort_relative_in_force_sorted_sections=True with reverse_relative=True and False
    config = Config(sort_relative_in_force_sorted_sections=True, reverse_relative=True)
    res1 = section_key("from ..foo import bar", config)

    config = Config(sort_relative_in_force_sorted_sections=True, reverse_relative=False)
    res2 = section_key("from ..foo import bar", config)
    assert res1 != res2

    # 5. Test line 80: force_to_top matching
    config = Config(force_to_top=["os"])
    res = section_key("os import path", config)
    # Should result in section 'A'
    assert res.startswith("A")

    # 6. Test lines 86-94: honor_case_in_force_sorted_sections=True, case_sensitive != order_by_type, len(split_module) > 1
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res = section_key("ModuleA import NameB", config)
    # case_sensitive is False -> module_name lowercased; order_by_type is True -> names unchanged
    assert "modulea import NameB" in res

    config2 = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
    )
    res2 = section_key("ModuleA import NameB", config2)
    # case_sensitive is True -> module_name unchanged; order_by_type is False -> names lowercased
    assert "ModuleA import nameb" in res2

    # 7. Test lines 95-96: honor_case_in_force_sorted_sections=True, case_sensitive != order_by_type, len(split_module) <= 1, case_sensitive=False
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res = section_key("ModuleA", config)
    assert res.endswith("modulea")

    # 8. Test lines 97-98: elif not config.order_by_type (when honor_case is False or case_sensitive == order_by_type)
    config = Config(
        honor_case_in_force_sorted_sections=False,
        order_by_type=False,
    )
    res = section_key("ModuleA import NameB", config)
    assert res.endswith("modulea import nameb")

    # 9. Test line 100 length_sort=True
    config = Config(length_sort=True)
    res = section_key("os", config)
    # Should include the length of the processed line right after section letter 'B'
    assert res.startswith("B2")
