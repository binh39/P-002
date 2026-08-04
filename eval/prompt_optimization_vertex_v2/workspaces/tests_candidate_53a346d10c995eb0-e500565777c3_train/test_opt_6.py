# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [97, 98], [97, 100]]}

import pytest
from isort.sorting import section_key
from isort.settings import Config


def test_section_key_full_coverage():
    # 1. Test lines 61-68:
    # not config.sort_relative_in_force_sorted_sections and config.reverse_relative and line.startswith("from .")
    config1 = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=True,
    )
    res1 = section_key("from .module import foo", config1)
    assert ". module import foo" in res1

    # 2. Test line 69-70:
    # config.group_by_package and line.strip().startswith("from")
    config2 = Config(group_by_package=True)
    res2 = section_key("from os import path", config2)
    assert res2 == "Bos"

    # 3. Test lines 72-73:
    # config.lexicographical = True
    config3 = Config(lexicographical=True)
    res3 = section_key("import os", config3)
    # Just verify it runs through lexicographical branch
    assert isinstance(res3, str)

    # 4. Test lines 77-79:
    # config.sort_relative_in_force_sorted_sections = True, reverse_relative = True / False
    config4_true = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=True,
    )
    res4_t = section_key("from ..module import foo", config4_true)
    assert ".. " in res4_t

    config4_false = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=False,
    )
    res4_f = section_key("from ..module import foo", config4_false)
    assert ".._" in res4_f

    # 5. Test line 80:
    # line.split(" ")[0] in config.force_to_top
    config5 = Config(force_to_top=["os"])
    res5 = section_key("import os", config5)
    assert res5.startswith("A")

    # 6. Test lines 86-94:
    # honor_case_in_force_sorted_sections=True, case_sensitive!=order_by_type, len(split_module) > 1
    config6 = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res6 = section_key("MyModule import Foo, Bar", config6)
    assert "mymodule import Foo, Bar" in res6

    # Test case_sensitive=True, order_by_type=False with len(split_module) > 1
    config6_b = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
    )
    res6_b = section_key("MyModule import Foo, Bar", config6_b)
    assert "MyModule import foo, bar" in res6_b

    # 7. Test lines 95-96:
    # honor_case_in_force_sorted_sections=True, case_sensitive!=order_by_type, len(split_module) <= 1, case_sensitive=False
    config7 = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res7 = section_key("MYMODULE", config7)
    assert res7 == "Bmymodule"

    # 8. Test lines 97-98:
    # elif not config.order_by_type:
    config8 = Config(
        honor_case_in_force_sorted_sections=False,
        order_by_type=False,
    )
    res8 = section_key("MyModule", config8)
    assert res8 == "Bmymodule"

    # 9. Test length_sort branch in return statement:
    config9 = Config(length_sort=True)
    res9 = section_key("os", config9)
    assert "2" in res9  # len("os") == 2
