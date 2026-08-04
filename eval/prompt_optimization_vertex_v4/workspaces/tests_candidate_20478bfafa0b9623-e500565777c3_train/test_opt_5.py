# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [97, 98], [97, 100]]}

import pytest
from isort.settings import Config
from isort.sorting import section_key

def test_section_key_reverse_relative():
    config = Config(reverse_relative=True, sort_relative_in_force_sorted_sections=False)
    line = "from .module import name"
    res = section_key(line, config)
    assert res == "B. module import name"

def test_section_key_group_by_package():
    config = Config(group_by_package=True)
    line = "from module import name"
    res = section_key(line, config)
    assert res == "Bmodule"

def test_section_key_lexicographical():
    config = Config(lexicographical=True)
    line = "import module"
    res = section_key(line, config)
    assert isinstance(res, str)

def test_section_key_sort_relative_in_force_sorted_sections():
    config = Config(sort_relative_in_force_sorted_sections=True, reverse_relative=True)
    line = "from ..module import name"
    res = section_key(line, config)
    assert ".." in res

def test_section_key_force_to_top():
    config = Config(force_to_top=["topmodule"])
    line = "topmodule import something"
    res = section_key(line, config)
    assert res.startswith("A")

def test_section_key_honor_case_split_module():
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True
    )
    line = "MyModule import SubName"
    res = section_key(line, config)
    assert "mymodule import SubName" in res

def test_section_key_honor_case_split_module_order_false():
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False
    )
    line = "MyModule import SubName"
    res = section_key(line, config)
    assert "MyModule import subname" in res

def test_section_key_honor_case_no_split():
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True
    )
    line = "MyModule"
    res = section_key(line, config)
    assert res == "Bmymodule"

def test_section_key_order_by_type_false_branch():
    config = Config(
        honor_case_in_force_sorted_sections=False,
        order_by_type=False
    )
    line = "MyModule import SubName"
    res = section_key(line, config)
    assert res == "Bmymodule import subname"

def test_section_key_length_sort():
    config = Config(length_sort=True)
    line = "module import name"
    res = section_key(line, config)
    assert "B18" in res
