# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47]]}

import pytest
from isort.sorting import module_key
from isort.settings import Config


def test_module_key_comprehensive():
    # Test line 23 & 24: match with reverse_relative = True
    config = Config(reverse_relative=True)
    res = module_key(".os", config)
    assert "." in res or "_" in res or " " in res

    # Test line 23 & 24 (False): match with reverse_relative = False
    config = Config(reverse_relative=False)
    res = module_key(".os", config)

    # Test line 28 & 29: ignore_case = True
    config = Config()
    res = module_key("OS", config, ignore_case=True)

    # Test lines 33-45: sub_imports and order_by_type branches
    # constants branch
    config = Config(order_by_type=True, constants=["MY_CONST"])
    res = module_key("MY_CONST", config, sub_imports=True)
    assert res.startswith("B")  # force_to_top False ('B'), prefix 'A'

    # classes branch
    config = Config(order_by_type=True, classes=["MyClass"])
    res = module_key("MyClass", config, sub_imports=True)

    # variables branch
    config = Config(order_by_type=True, variables=["my_var"])
    res = module_key("my_var", config, sub_imports=True)

    # isupper() and len > 1 branch
    config = Config(order_by_type=True)
    res = module_key("ABC", config, sub_imports=True)

    # classes or module_name[0:1].isupper() branch
    config = Config(order_by_type=True)
    res = module_key("Abc", config, sub_imports=True)

    # else branch (lowercase, length <= 1 or not upper)
    config = Config(order_by_type=True)
    res = module_key("abc", config, sub_imports=True)

    # Test line 46 & 47: not config.case_sensitive
    config = Config(case_sensitive=False)
    res = module_key("ABC", config)

    # Test lines 49-52: length_sort combinations
    # config.length_sort = True
    config = Config(length_sort=True)
    res = module_key("abc", config)

    # config.length_sort_straight and straight_import = True
    config = Config(length_sort_straight=True)
    res = module_key("abc", config, straight_import=True)

    # section_name in config.length_sort_sections
    config = Config(length_sort_sections=["thirdparty"])
    res = module_key("abc", config, section_name="THIRDPARTY")

    # Test line 55: module_name in config.force_to_top
    config = Config(force_to_top=["os"])
    res = module_key("os", config)
    assert res.startswith("A")
