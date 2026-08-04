# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [97, 98], [97, 100]]}

from isort.settings import Config
from isort.sorting import section_key


def test_section_key_comprehensive():
    # 1. Test reverse_relative and line starts with "from ." (lines 61-64)
    config = Config(reverse_relative=True, sort_relative_in_force_sorted_sections=False)
    line = "from .foo import bar"
    res = section_key(line, config)
    assert res.startswith("B")

    # 2. Test group_by_package and line starts with "from" (line 69)
    config = Config(group_by_package=True)
    line = "from foo import bar"
    res = section_key(line, config)
    assert "bar" not in res

    # 3. Test lexicographical=True (line 72)
    config = Config(lexicographical=True)
    line = "import os"
    res = section_key(line, config)
    assert res

    # 4. Test sort_relative_in_force_sorted_sections with reverse_relative=True vs False (lines 77-79)
    config1 = Config(sort_relative_in_force_sorted_sections=True, reverse_relative=True)
    config2 = Config(sort_relative_in_force_sorted_sections=True, reverse_relative=False)
    line = "from .. import foo"
    res1 = section_key(line, config1)
    res2 = section_key(line, config2)
    assert res1 != res2

    # 5. Test force_to_top matching (line 80)
    config = Config(force_to_top=["os"])
    line = "import os"
    res = section_key(line, config)
    assert res.startswith("A")

    # 6. Test honor_case_in_force_sorted_sections and case_sensitive != order_by_type (lines 86-96)
    # Case A: split_module > 1 (has import)
    config_a = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
    )
    line = "ModuleName import FuncName"
    res_a = section_key(line, config_a)
    assert "funcname" in res_a

    config_b = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    line = "ModuleName import FuncName"
    res_b = section_key(line, config_b)
    assert "modulename" in res_b

    # Case B: split_module <= 1 (no import)
    config_c = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    line = "ModuleNameOnly"
    res_c = section_key(line, config_c)
    assert "modulenameonly" in res_c

    # 7. Test elif not config.order_by_type (lines 97-98)
    config_d = Config(
        honor_case_in_force_sorted_sections=False,
        order_by_type=False,
    )
    line = "SomeModule"
    res_d = section_key(line, config_d)
    assert "somemodule" in res_d

    # 8. Test length_sort = True (line 100)
    config_len = Config(length_sort=True)
    line = "import os"
    res_len = section_key(line, config_len)
    assert str(len("os")) in res_len
