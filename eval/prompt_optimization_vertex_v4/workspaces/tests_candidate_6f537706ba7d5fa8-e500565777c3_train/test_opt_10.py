# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [97, 98], [97, 100]]}

from isort.sorting import section_key
from isort.settings import Config

def test_section_key_comprehensive():
    # 1. Test reverse_relative and startswith "from ." without sort_relative_in_force_sorted_sections
    config_rev = Config(reverse_relative=True, sort_relative_in_force_sorted_sections=False)
    res = section_key("from .module import name", config_rev)
    assert res == "B. module import name"

    # 2. Test group_by_package with "from"
    config_group = Config(group_by_package=True)
    res = section_key("from os import path", config_group)
    assert res == "Bos"

    # 3. Test lexicographical sorting
    config_lex = Config(lexicographical=True)
    res = section_key("import os", config_lex)
    assert "os" in res

    # 4. Test sort_relative_in_force_sorted_sections with reverse_relative=True and False
    config_srev = Config(sort_relative_in_force_sorted_sections=True, reverse_relative=True)
    res = section_key("from .module import name", config_srev)
    assert "B" in res

    config_snotrev = Config(sort_relative_in_force_sorted_sections=True, reverse_relative=False)
    res2 = section_key("from .module import name", config_snotrev)
    assert "B" in res2

    # 5. Test force_to_top matching first split word
    config_top = Config(force_to_top=["foo"])
    res = section_key("foo import bar", config_top)
    assert res.startswith("A")

    # 6. Test honor_case_in_force_sorted_sections and case_sensitive != order_by_type with " import "
    config_honor_split = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False
    )
    res = section_key("Foo import Bar", config_honor_split)
    assert "bar" in res  # names lowercased, module name kept

    config_honor_split2 = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True
    )
    res = section_key("Foo import Bar", config_honor_split2)
    assert "foo" in res  # module name lowercased, names kept

    # 7. Test honor_case_in_force_sorted_sections and case_sensitive != order_by_type without " import " (e.g. simple import line)
    config_honor_no_split = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True
    )
    res = section_key("FooBar", config_honor_no_split)
    assert res == "Bfoobar"

    # 8. Test elif not config.order_by_type (when honor_case... is False)
    config_no_order = Config(
        honor_case_in_force_sorted_sections=False,
        order_by_type=False
    )
    res = section_key("FooBar", config_no_order)
    assert res == "Bfoobar"

    # 9. Test length_sort enabled
    config_len = Config(length_sort=True)
    res = section_key("os", config_len)
    assert "2" in res  # len("os") == 2
