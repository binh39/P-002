# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [92, 94], [95, 96], [97, 98], [97, 100]]}

import pytest
from isort.settings import Config
from isort.sorting import section_key


def test_section_key_full_coverage():
    # 1. Test lines 61-68: sort_relative_in_force_sorted_sections=False, reverse_relative=True, line starts with "from ."
    config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=True,
    )
    res = section_key("from .foo import bar", config)
    assert isinstance(res, str)

    # 2. Test line 69-70: group_by_package=True, line starts with "from"
    config = Config(group_by_package=True)
    res = section_key("from foo import bar", config)
    assert "import" not in res

    # 3. Test lines 72-73: lexicographical=True
    config = Config(lexicographical=True)
    res = section_key("import os", config)
    assert isinstance(res, str)

    # 4. Test lines 77-79: sort_relative_in_force_sorted_sections=True with reverse_relative=False and True
    config = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=False,
    )
    res = section_key("from .foo import bar", config)
    assert isinstance(res, str)

    config_rev = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=True,
    )
    res_rev = section_key("from .foo import bar", config_rev)
    assert isinstance(res_rev, str)

    # 5. Test line 80: force_to_top matches first word
    config = Config(force_to_top=("os",))
    res = section_key("os", config)
    assert res.startswith("A")

    # 6. Test lines 86-94: honor_case_in_force_sorted_sections=True, case_sensitive != order_by_type (with " import ")
    # case_sensitive=False, order_by_type=True
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res = section_key("Foo import Bar", config)
    assert isinstance(res, str)

    # 7. Test lines 95-96: honor_case_in_force_sorted_sections=True, case_sensitive != order_by_type (without " import ")
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res = section_key("FooBar", config)
    assert isinstance(res, str)

    # 8. Test lines 97-98: elif not config.order_by_type (when honor_case condition is False)
    config = Config(
        honor_case_in_force_sorted_sections=False,
        order_by_type=False,
    )
    res = section_key("FooBar", config)
    assert res == "Bfoobar"

    # 9. Test line 100 length_sort=True
    config = Config(length_sort=True)
    res = section_key("os", config)
    assert "2" in res
