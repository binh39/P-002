# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

import pytest
from isort.sorting import module_key
from isort.settings import Config


def test_module_key_all_branches():
    # 1. match relative with reverse_relative = True and False
    config_rev = Config(reverse_relative=True)
    res_rev = module_key(".foo", config_rev)
    # With reverse_relative=True, sep is " ", so groups become (".", "foo") joined by " " -> ". foo"
    assert " " in res_rev

    config_norm = Config(reverse_relative=False)
    res_norm = module_key(".foo", config_norm)
    # With reverse_relative=False, sep is "_", so groups become (".", "foo") joined by "_" -> "._foo"
    assert "_" in res_norm

    # 2. ignore_case = True vs False
    config_case = Config(case_sensitive=True)
    res_ignore = module_key("FOO", config_case, ignore_case=True)
    assert res_ignore.endswith("foo")

    res_no_ignore = module_key("FOO", config_case, ignore_case=False)
    assert res_no_ignore.endswith("FOO")

    # 3. sub_imports & order_by_type paths:
    # constants, classes, variables, isupper len > 1, classes/isupper first letter, else
    config_order = Config(
        order_by_type=True,
        constants=["const"],
        classes=["myclass"],
        variables=["var"],
    )

    # constants ('A')
    assert "A" in module_key("const", config_order, sub_imports=True)
    # classes ('B')
    assert "B" in module_key("myclass", config_order, sub_imports=True)
    # variables ('C')
    assert "C" in module_key("var", config_order, sub_imports=True)
    # isupper len > 1 ('A')
    assert "A" in module_key("ABC", config_order, sub_imports=True)
    # classes or upper first letter ('B')
    assert "B" in module_key("Someclass", config_order, sub_imports=True)
    # else ('C')
    assert "C" in module_key("other", config_order, sub_imports=True)

    # 4. not config.case_sensitive
    config_insensitive = Config(case_sensitive=False)
    res_insens = module_key("Foo", config_insensitive)
    assert res_insens.endswith("foo")

    # 5. length_sort branches:
    # config.length_sort
    config_len1 = Config(length_sort=True)
    assert ":" in module_key("foo", config_len1)

    # config.length_sort_straight and straight_import
    config_len2 = Config(length_sort_straight=True)
    assert ":" in module_key("foo", config_len2, straight_import=True)

    # str(section_name).lower() in config.length_sort_sections
    config_len3 = Config(length_sort_sections=["mysched"])
    assert ":" in module_key("foo", config_len3, section_name="MySched")

    # 6. force_to_top ('A' vs 'B')
    config_force = Config(force_to_top=["topmod"])
    res_top = module_key("topmod", config_force)
    assert res_top.startswith("A")

    res_not_top = module_key("othermod", config_force)
    assert res_not_top.startswith("B")
