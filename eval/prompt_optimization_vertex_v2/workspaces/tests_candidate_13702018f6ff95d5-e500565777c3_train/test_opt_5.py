# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [97, 98], [97, 100]]}

import pytest
from isort.settings import Config
from isort.sorting import section_key


def test_section_key_comprehensive():
    # 1. Test sort_relative_in_force_sorted_sections = False, reverse_relative = True, line starts with "from ."
    config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=True,
    )
    res = section_key("from .module import name", config)
    assert res == "B. module import name"

    # 2. Test group_by_package = True, line starts with "from"
    config = Config(group_by_package=True)
    res = section_key("from os import path", config)
    assert res == "Bos"

    # 3. Test lexicographical = True
    config = Config(lexicographical=True)
    res = section_key("import os", config)
    assert res.startswith("B")

    # 4. Test sort_relative_in_force_sorted_sections = True with reverse_relative = True and False
    config = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=True,
    )
    res = section_key("from ..foo import bar", config)
    assert ".." in res

    config = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=False,
    )
    res = section_key("from ..foo import bar", config)
    assert ".." in res

    # 5. Test force_to_top match
    config = Config(force_to_top=["os"])
    res = section_key("import os", config)
    assert res.startswith("A")

    # 6. Test honor_case_in_force_sorted_sections = True and case_sensitive != order_by_type
    # Case A: len(split_module) > 1
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
    )
    res = section_key("import MyModule import MyNames", config)
    assert "mynames" in res

    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res = section_key("import MyModule import MyNames", config)
    assert "mymodule" in res

    # Case B: len(split_module) <= 1 (no " import ")
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res = section_key("import MyModuleOnly", config)
    assert res == "Bmymoduleonly"

    # 7. Test elif not config.order_by_type (when honor_case... is False)
    config = Config(
        honor_case_in_force_sorted_sections=False,
        order_by_type=False,
    )
    res = section_key("import MyModule", config)
    assert res == "Bmymodule"

    # 8. Test length_sort = True
    config = Config(length_sort=True)
    res = section_key("import os", config)
    assert "2" in res  # len("os") == 2
