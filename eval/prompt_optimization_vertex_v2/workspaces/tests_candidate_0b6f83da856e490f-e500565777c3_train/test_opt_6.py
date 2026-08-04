# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

import pytest
from isort.settings import Config
from isort.sorting import module_key


def test_module_key_comprehensive():
    # Test relative module name with reverse_relative = True and False
    config_default = Config()
    
    # 1. relative import with reverse_relative = False (default)
    res1 = module_key(".foo", config_default)
    assert "_foo" in res1

    config_rev = Config(reverse_relative=True)
    res2 = module_key(".foo", config_rev)
    assert " .foo" in res2 or ". foo" in res2 or " " in res2  # sep = " "

    # 2. ignore_case = True vs False
    res_ignore = module_key("FOO", config_default, ignore_case=True)
    assert res_ignore.endswith("foo")

    # By default, config.case_sensitive is False in isort Config, so "FOO" gets lowercased.
    # To test ignore_case=False keeping uppercase, we need case_sensitive=True.
    config_sensitive = Config(case_sensitive=True)
    res_no_ignore = module_key("FOO", config_sensitive, ignore_case=False)
    assert res_no_ignore.endswith("FOO")

    # 3. sub_imports and order_by_type branches
    # constants, classes, variables, isupper len > 1, classes/upper, else
    config_order = Config(
        order_by_type=True,
        constants=["CONST"],
        classes=["MyClass"],
        variables=["var"],
    )

    # constant
    assert "A" in module_key("CONST", config_order, sub_imports=True)
    # class
    assert "B" in module_key("MyClass", config_order, sub_imports=True)
    # variable
    assert "C" in module_key("var", config_order, sub_imports=True)
    # isupper and len > 1 -> 'A'
    assert "A" in module_key("UPPER", config_order, sub_imports=True)
    # in config.classes or starts with upper -> 'B' (already covered by MyClass or can test another upper like "Other")
    assert "B" in module_key("Other", config_order, sub_imports=True)
    # else -> 'C' (e.g. lowercase not in vars/constants/classes)
    assert "C" in module_key("lowercase", config_order, sub_imports=True)

    # 4. case_sensitive = False
    config_insensitive = Config(case_sensitive=False)
    res_sens = module_key("Bar", config_insensitive)
    assert "bar" in res_sens

    # 5. length_sort branches:
    # config.length_sort
    config_ls = Config(length_sort=True)
    assert ":" in module_key("foo", config_ls)

    # config.length_sort_straight and straight_import
    config_lss = Config(length_sort_straight=True)
    assert ":" in module_key("foo", config_lss, straight_import=True)

    # str(section_name).lower() in config.length_sort_sections
    config_lss_sec = Config(length_sort_sections=["thirdparty"])
    assert ":" in module_key("foo", config_lss_sec, section_name="ThirdParty")

    # 6. force_to_top -> 'A' else 'B'
    config_top = Config(force_to_top=["topmodule"])
    assert module_key("topmodule", config_top).startswith("A")
    assert module_key("othermodule", config_top).startswith("B")
