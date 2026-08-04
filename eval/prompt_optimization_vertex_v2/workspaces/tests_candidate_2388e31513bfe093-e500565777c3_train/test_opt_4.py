# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [97, 98], [97, 100]]}

import pytest
from isort.settings import Config
from isort.sorting import section_key


def test_section_key_basic():
    config = Config()
    # default config: lexicographical=False, sort_relative_in_force_sorted_sections=False, etc.
    # "import os" has "import " stripped by re.sub('^import ', '', line), leaving "os"
    res = section_key("import os", config)
    assert res == "Bos"


def test_reverse_relative_transformation():
    config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=True,
    )
    line = "from .module import name"
    res = section_key(line, config)
    assert res.startswith("B")


def test_group_by_package():
    config = Config(group_by_package=True)
    line = "from package import sub"
    res = section_key(line, config)
    # group_by_package splits at ' import ', taking the first part: 'from package'
    # Then sub '^from ' removes 'from ', leaving 'package'
    assert res == "Bpackage"


def test_lexicographical_mode():
    config = Config(lexicographical=True)
    line = "import os"
    res = section_key(line, config)
    assert res.startswith("B")


def test_sort_relative_in_force_sorted_sections():
    # Test with reverse_relative=True (sep = ' ') and False (sep = '_')
    config_true = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=True,
    )
    res1 = section_key("from ..os import path", config_true)

    config_false = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=False,
    )
    res2 = section_key("from ..os import path", config_false)

    assert res1.startswith("B")
    assert res2.startswith("B")


def test_force_to_top():
    config = Config(force_to_top=["sys"])
    res = section_key("import sys", config)
    assert res.startswith("A")


def test_honor_case_in_force_sorted_sections_with_import_split():
    # honor_case_in_force_sorted_sections = True, case_sensitive != order_by_type
    # case_sensitive = False, order_by_type = True -> case_sensitive != order_by_type is True
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    # len(split_module) > 1 case
    res = section_key("MyModule import NameA, nameB", config)
    assert "mymodule import NameA, nameB" in res

    # order_by_type = False, case_sensitive = True -> case_sensitive != order_by_type is True
    config2 = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
    )
    res2 = section_key("MyModule import NameA, nameB", config2)
    assert "MyModule import namea, nameb" in res2


def test_honor_case_in_force_sorted_sections_without_import_split():
    # len(split_module) == 1, case_sensitive = False
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res = section_key("MyModule", config)
    assert "mymodule" in res


def test_order_by_type_false_fallback():
    # honor_case_in_force_sorted_sections = False, order_by_type = False
    config = Config(
        honor_case_in_force_sorted_sections=False,
        order_by_type=False,
    )
    res = section_key("import MyModule", config)
    assert "mymodule" in res


def test_length_sort():
    config = Config(length_sort=True)
    res = section_key("import os", config)
    # Should include length of the processed line between 'B' and the line itself
    # 'import os' -> 'os', len('os') is 2, so 'B2os'
    assert res == "B2os"
