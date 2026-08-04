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
    assert "import" not in res

    # 3. Test lexicographical sorting (line 72-73)
    config = Config(lexicographical=True)
    line = "import b, a"
    res = section_key(line, config)
    assert isinstance(res, str)

    # 4. Test sort_relative_in_force_sorted_sections with reverse_relative=True and False (lines 77-79)
    config1 = Config(sort_relative_in_force_sorted_sections=True, reverse_relative=True)
    res1 = section_key("from .foo import bar", config1)
    
    config2 = Config(sort_relative_in_force_sorted_sections=True, reverse_relative=False)
    res2 = section_key("from .foo import bar", config2)
    assert res1 != res2

    # 5. Test force_to_top (lines 80-81)
    config = Config(force_to_top=["module"])
    res = section_key("module import something", config)
    assert res.startswith("A")

    # 6. Test honor_case_in_force_sorted_sections with case_sensitive != order_by_type (lines 86-96)
    # Split module > 1 case
    config_hc1 = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res = section_key("MyModule import Name", config_hc1)
    assert "mymodule" in res
    assert "Name" in res

    config_hc2 = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
    )
    res = section_key("MyModule import Name", config_hc2)
    assert "MyModule" in res
    assert "name" in res

    # Split module <= 1 (no import) case with case_sensitive=False
    config_hc3 = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res = section_key("MyModule", config_hc3)
    assert res == "BMymodule" or "mymodule" in res

    # 7. Test elif not config.order_by_type (lines 97-98)
    config_order = Config(
        honor_case_in_force_sorted_sections=False,
        order_by_type=False,
    )
    res = section_key("MyModule import Name", config_order)
    assert res == "Bmymodule import name"

    # 8. Test length_sort=True (line 100)
    config_length = Config(length_sort=True)
    res = section_key("os", config_length)
    assert "2" in res
