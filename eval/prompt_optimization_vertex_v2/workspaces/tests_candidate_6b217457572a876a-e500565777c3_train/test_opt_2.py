# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [97, 98], [97, 100]]}

import pytest
from isort.sorting import section_key
from isort.settings import Config


def test_section_key_full_coverage():
    # 1. Test reverse_relative and line starting with "from ."
    config1 = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=True,
        group_by_package=False,
        lexicographical=False,
        length_sort=False,
    )
    res1 = section_key("from .module import foo", config1)
    assert res1.startswith("B")

    # 2. Test group_by_package with line starting with "from"
    config2 = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=True,
        lexicographical=False,
        length_sort=False,
    )
    res2 = section_key("from os import path", config2)
    assert "import" not in res2

    # 3. Test lexicographical config
    config3 = Config(
        lexicographical=True,
        length_sort=False,
    )
    res3 = section_key("import os", config3)
    assert isinstance(res3, str)

    # 4. Test sort_relative_in_force_sorted_sections with reverse_relative True and False
    config4a = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=True,
        length_sort=False,
    )
    res4a = section_key("from ..foo import bar", config4a)
    assert isinstance(res4a, str)

    config4b = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=False,
        length_sort=False,
    )
    res4b = section_key("from ..foo import bar", config4b)
    assert isinstance(res4b, str)

    # 5. Test force_to_top matching (section = "A")
    config5 = Config(
        force_to_top=("os",),
        length_sort=False,
    )
    res5 = section_key("import os", config5)
    assert res5.startswith("A")

    # 6. Test honor_case_in_force_sorted_sections and case_sensitive != order_by_type
    # case_sensitive = False, order_by_type = True
    config6a = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
        length_sort=False,
    )
    res6a = section_key("Module import Names", config6a)
    assert "module import Names" in res6a

    # case_sensitive = True, order_by_type = False
    config6b = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
        length_sort=False,
    )
    res6b = section_key("Module import Names", config6b)
    assert "Module import names" in res6b

    # case_sensitive = False, order_by_type = False (split_module length <= 1, case_sensitive = False)
    config6c = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
        length_sort=False,
    )
    res6c = section_key("Module", config6c)
    assert "module" in res6c

    # 7. Test elif not config.order_by_type
    config7 = Config(
        honor_case_in_force_sorted_sections=False,
        order_by_type=False,
        length_sort=True,
    )
    res7 = section_key("import OS", config7)
    assert res7.startswith("B")

    # 8. Test length_sort = True normally without honor_case branches
    config8 = Config(
        length_sort=True,
        order_by_type=True,
        case_sensitive=True,
    )
    res8 = section_key("import os", config8)
    # Check that length is included in the string between section and line content
    assert res8[0] == "B"
    assert res8[1].isdigit()
