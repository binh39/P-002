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
    res1 = section_key("from .module import foo", config1)
    assert "module" in res1

    # 2. Test group_by_package and line.strip().startswith("from")
    config2 = Config(group_by_package=True)
    res2 = section_key("from os import path", config2)
    assert "import" not in res2

    # 3. Test lexicographical=True vs False
    config3 = Config(lexicographical=True)
    res3 = section_key("import os", config3)

    config4 = Config(lexicographical=False)
    res4 = section_key("import os", config4)
    assert res4.startswith("B")

    # 4. Test sort_relative_in_force_sorted_sections with reverse_relative True and False
    config5 = Config(sort_relative_in_force_sorted_sections=True, reverse_relative=True)
    res5 = section_key("...module", config5)
    assert "..." in res5

    config6 = Config(sort_relative_in_force_sorted_sections=True, reverse_relative=False)
    res6 = section_key("...module", config6)
    assert "..." in res6

    # 5. Test force_to_top
    config7 = Config(force_to_top=["os"])
    res7 = section_key("import os", config7)
    assert res7.startswith("A")

    # 6. Test honor_case_in_force_sorted_sections and case_sensitive != order_by_type
    # With len(split_module) > 1
    config8 = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res8 = section_key("OS import FOO", config8)
    assert "os import FOO" in res8

    config9 = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
    )
    res9 = section_key("OS import FOO", config9)
    assert "OS import foo" in res9

    # Without split_module > 1 (i.e. len == 1)
    config10 = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res10 = section_key("OSModule", config10)
    assert "osmodule" in res10

    # 7. Test elif not config.order_by_type (when honor_case_in_force_sorted_sections is False)
    config11 = Config(
        honor_case_in_force_sorted_sections=False,
        order_by_type=False,
    )
    res11 = section_key("OSMODULE", config11)
    assert "osmodule" in res11

    # 8. Test length_sort
    config12 = Config(length_sort=True)
    res12 = section_key("os", config12)
    # Should include length (2) between 'B' and line
    assert res12 == "B2os"
