# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}

import pytest
from isort.settings import Config
from isort.sorting import section_key


def test_section_key_comprehensive():
    # 1. Test reverse_relative and not sort_relative_in_force_sorted_sections
    config1 = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=True,
        group_by_package=False,
        lexicographical=False,
    )
    res1 = section_key("from . module import name", config1)
    assert res1.startswith("B")

    # 2. Test group_by_package with 'from'
    config2 = Config(
        group_by_package=True,
        lexicographical=False,
    )
    res2 = section_key("from os import path", config2)
    assert "import" not in res2

    # 3. Test lexicographical=True
    config3 = Config(
        lexicographical=True,
    )
    res3 = section_key("import os", config3)
    assert isinstance(res3, str)

    # 4. Test sort_relative_in_force_sorted_sections with reverse_relative=True and False
    config4_true = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=True,
    )
    res4_true = section_key("from . import x", config4_true)

    config4_false = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=False,
    )
    res4_false = section_key("from . import x", config4_false)
    assert res4_true != res4_false

    # 5. Test force_to_top -> section = 'A'
    config5 = Config(
        force_to_top=["os"],
    )
    res5 = section_key("import os", config5)
    assert res5.startswith("A")

    # 6. Test honor_case_in_force_sorted_sections and case_sensitive != order_by_type
    # case_sensitive = False, order_by_type = True (differs)
    config6_a = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res6_a1 = section_key("OS import Name", config6_a)
    res6_a2 = section_key("OS", config6_a)
    assert isinstance(res6_a1, str)
    assert isinstance(res6_a2, str)

    # case_sensitive = True, order_by_type = False (differs)
    config6_b = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
    )
    res6_b1 = section_key("OS import Name", config6_b)
    res6_b2 = section_key("OS", config6_b)
    assert isinstance(res6_b1, str)
    assert isinstance(res6_b2, str)

    # 7. Test elif not config.order_by_type (honor_case_in_force_sorted_sections = False, order_by_type = False)
    config7 = Config(
        honor_case_in_force_sorted_sections=False,
        order_by_type=False,
    )
    res7 = section_key("IMPORT OS", config7)
    assert res7 == "Bimport os"  # 'import ' is stripped before the elif block, but the keyword 'import' remains in the module name "IMPORT OS" (lowercased)

    # 8. Test length_sort = True
    config8 = Config(
        length_sort=True,
    )
    res8 = section_key("import os", config8)
    assert len(res8) > len("os")
