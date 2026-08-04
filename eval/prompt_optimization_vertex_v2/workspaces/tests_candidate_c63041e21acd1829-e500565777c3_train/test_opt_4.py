# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [90, 91], [90, 92], [92, 93], [92, 94], [97, 98], [97, 100]]}

import pytest
from isort.sorting import section_key
from isort.settings import Config


def test_section_key_branches():
    # 1. Test reverse_relative and not sort_relative_in_force_sorted_sections with "from ."
    config1 = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=True,
    )
    res1 = section_key("from .module import something", config1)
    assert res1.startswith("B")

    # 2. Test group_by_package and line starting with "from"
    config2 = Config(
        group_by_package=True,
    )
    res2 = section_key("from os import path", config2)
    assert "import" not in res2

    # 3. Test lexicographical=True
    config3 = Config(
        lexicographical=True,
    )
    res3 = section_key("import os", config3)
    assert res3

    # 4. Test sort_relative_in_force_sorted_sections=True with reverse_relative=True & False
    config4a = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=True,
    )
    res4a = section_key("from .module import x", config4a)
    assert res4a

    config4b = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=False,
    )
    res4b = section_key("from .module import x", config4b)
    assert res4b

    # 5. Test force_to_top triggering section = "A"
    config5 = Config(
        force_to_top=["os"],
    )
    res5 = section_key("os import path", config5)
    assert res5.startswith("A")

    # 6. Test honor_case_in_force_sorted_sections and case_sensitive != order_by_type
    # Case A: len(split_module) > 1 with case_sensitive=True, order_by_type=False
    config6a = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
    )
    res6a = section_key("OS import Path", config6a)
    assert "path" in res6a

    # Case A2: len(split_module) > 1 with case_sensitive=False, order_by_type=True
    config6b = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res6b = section_key("OS import Path", config6b)
    assert "Path" in res6b

    # Case B: len(split_module) <= 1, not case_sensitive
    config6c = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=False,
    )
    res6c = section_key("OSMODULE", config6c)
    assert res6c.endswith("osmodule")

    # 7. Test elif not config.order_by_type (when honor_case... is False)
    config7 = Config(
        honor_case_in_force_sorted_sections=False,
        order_by_type=False,
    )
    res7 = section_key("OSModule", config7)
    assert res7.endswith("osmodule")

    # 8. Test length_sort = True
    config8 = Config(
        length_sort=True,
    )
    res8 = section_key("os", config8)
    # length of "os" after removing "import " is 2
    assert "2" in res8
