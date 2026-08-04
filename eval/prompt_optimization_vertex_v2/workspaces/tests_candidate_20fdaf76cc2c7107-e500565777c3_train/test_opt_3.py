# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [97, 98], [97, 100]]}

import pytest
from isort.settings import Config
from isort.sorting import section_key

def test_section_key_default():
    config = Config()
    # default config: 
    # sort_relative_in_force_sorted_sections = False
    # reverse_relative = False
    # group_by_package = False
    # lexicographical = False
    # length_sort = False
    # case_sensitive = False (or default)
    # order_by_type = True
    # force_to_top = ()
    res = section_key("import os", config)
    # line becomes "os", order_by_type is True, case_sensitive is False -> elif not config.order_by_type is False
    assert res == "Bos"

def test_section_key_reverse_relative():
    config = Config(reverse_relative=True)
    # not sort_relative_in_force_sorted_sections (True) and reverse_relative (True) and line.startswith("from .")
    res = section_key("from .module import foo", config)
    # match groups: (".", "module import foo"), line becomes "from . module import foo"
    assert "module" in res

def test_section_key_group_by_package():
    config = Config(group_by_package=True)
    res = section_key("from os import path", config)
    # group_by_package and starts with "from" -> line becomes "from os"
    assert "os" in res

def test_section_key_lexicographical():
    config = Config(lexicographical=True)
    res = section_key("import os.path", config)
    assert res.startswith("B")

def test_section_key_sort_relative_in_force_sorted_sections():
    config = Config(sort_relative_in_force_sorted_sections=True, reverse_relative=True)
    res = section_key("from ...module import foo", config)
    assert res.startswith("B")

def test_section_key_sort_relative_in_force_sorted_sections_no_reverse():
    config = Config(sort_relative_in_force_sorted_sections=True, reverse_relative=False)
    res = section_key("from ...module import foo", config)
    assert res.startswith("B")

def test_section_key_force_to_top():
    config = Config(force_to_top=("os",))
    res = section_key("import os", config)
    assert res.startswith("A")

def test_section_key_honor_case_split_module():
    # honor_case_in_force_sorted_sections=True, case_sensitive=False, order_by_type=True
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True
    )
    res = section_key("import ModuleA import NAMES", config)
    assert res.startswith("B")

def test_section_key_honor_case_split_module_case_sensitive_true_order_type_false():
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False
    )
    res = section_key("import ModuleA import NAMES", config)
    assert res.startswith("B")

def test_section_key_honor_case_no_split():
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True
    )
    res = section_key("import ModuleA", config)
    assert res.startswith("B")

def test_section_key_order_by_type_false_no_honor():
    config = Config(
        honor_case_in_force_sorted_sections=False,
        order_by_type=False
    )
    res = section_key("import ModuleA", config)
    assert res.startswith("B")

def test_section_key_length_sort():
    config = Config(length_sort=True)
    res = section_key("import os", config)
    assert "2" in res  # length of "os" is 2
