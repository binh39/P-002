# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [97, 98], [97, 100]]}

from isort.settings import Config
from isort.sorting import section_key


def test_section_key_comprehensive():
    # 1. Test reverse_relative and line starts with "from ." (lines 61-64)
    config = Config(reverse_relative=True, sort_relative_in_force_sorted_sections=False)
    res = section_key("from .foo import bar", config)
    assert ". foo" in res

    # 2. Test group_by_package and line starts with "from" (line 69)
    config = Config(group_by_package=True)
    res = section_key("from foo import bar", config)
    assert res == "Bfoo"

    # 3. Test lexicographical=True (line 72-73)
    config = Config(lexicographical=True)
    res = section_key("import foo", config)
    assert isinstance(res, str)

    # 4. Test sort_relative_in_force_sorted_sections=True with reverse_relative=True vs False (lines 77-79)
    config_rev = Config(sort_relative_in_force_sorted_sections=True, reverse_relative=True)
    res_rev = section_key("from ..foo import bar", config_rev)
    assert ".. " in res_rev

    config_no_rev = Config(sort_relative_in_force_sorted_sections=True, reverse_relative=False)
    res_no_rev = section_key("from ..foo import bar", config_no_rev)
    assert ".._" in res_no_rev

    # 5. Test force_to_top (lines 80-81)
    config = Config(force_to_top=["os"])
    res = section_key("os import path", config)
    assert res.startswith("A")

    # 6. Test honor_case_in_force_sorted_sections and case_sensitive != order_by_type (lines 86-96)
    # 6a. with ' import ' in line (split_module > 1)
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
    )
    res = section_key("from FOO import Bar", config)
    # case_sensitive=True -> module_name remains "FOO" (after "from " is stripped) -> "FOO"
    # order_by_type=False -> names become lower -> "bar"
    assert "FOO import bar" in res

    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res = section_key("from FOO import Bar", config)
    # case_sensitive=False -> module_name lower -> "foo"
    # order_by_type=True -> names unchanged -> "Bar"
    assert "foo import Bar" in res

    # 6b. without ' import ' in line (len(split_module) == 1), with case_sensitive=False
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res = section_key("import FOO", config)
    assert "foo" in res

    # 7. Test elif not config.order_by_type (lines 97-98)
    config = Config(
        honor_case_in_force_sorted_sections=False,
        order_by_type=False,
    )
    res = section_key("import FOO", config)
    assert "foo" in res

    # 8. Test length_sort=True (line 100)
    config = Config(length_sort=True)
    res = section_key("import foo", config)
    assert len(res) > len("Bfoo")
