# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [97, 98], [97, 100]]}

import pytest
from isort.settings import Config
from isort.sorting import section_key


def test_section_key_comprehensive():
    # 1. Test reverse_relative and startswith("from .")
    config1 = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=True,
    )
    res1 = section_key("from .foo import bar", config1)
    assert isinstance(res1, str)

    # 2. Test group_by_package and line.strip().startswith("from")
    config2 = Config(group_by_package=True)
    res2 = section_key("from foo import bar, baz", config2)
    assert "import" not in res2

    # 3. Test lexicographical
    config3 = Config(lexicographical=True)
    res3 = section_key("import os", config3)
    assert isinstance(res3, str)

    # 4. Test sort_relative_in_force_sorted_sections with reverse_relative True and False
    config4_true = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=True,
    )
    res4_true = section_key("from ..foo import bar", config4_true)
    assert isinstance(res4_true, str)

    config4_false = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=False,
    )
    res4_false = section_key("from ..foo import bar", config4_false)
    assert isinstance(res4_false, str)

    # 5. Test force_to_top triggering section = "A"
    config5 = Config(force_to_top=["foo"])
    res5 = section_key("foo import bar", config5)
    assert res5.startswith("A")

    # 6. Test honor_case_in_force_sorted_sections and case_sensitive != order_by_type
    # Branch with split_module > 1 (module and names)
    config6a = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
    )
    res6a = section_key("MyModule import MyNames", config6a)
    assert isinstance(res6a, str)

    config6b = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res6b = section_key("MyModule import MyNames", config6b)
    assert isinstance(res6b, str)

    # Branch with split_module len <= 1 (no " import ") and case_sensitive=False
    config6c = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res6c = section_key("MyModule", config6c)
    assert isinstance(res6c, str)

    # 7. Test elif not config.order_by_type (when honor_case_in_force_sorted_sections is False or case_sensitive == order_by_type)
    config7 = Config(
        honor_case_in_force_sorted_sections=False,
        order_by_type=False,
    )
    res7 = section_key("MyModule", config7)
    assert res7 == "Bmymodule"

    # 8. Test length_sort
    config8 = Config(length_sort=True)
    res8 = section_key("os", config8)
    assert "2" in res8
