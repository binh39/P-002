# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

import pytest
from isort.sorting import module_key
from isort.settings import Config


def test_module_key_comprehensive():
    # Test relative module name with reverse_relative = True and False
    config_default = Config()
    
    # 1. relative import with reverse_relative = True
    config_rev = Config(reverse_relative=True)
    res1 = module_key(".foo", config_rev)
    assert res1.startswith("B")

    # relative import with reverse_relative = False (default)
    res2 = module_key(".foo", config_default)
    assert res2.startswith("B")

    # 2. ignore_case = True vs False
    # By default, isort's Config sets case_sensitive = False, so module names are lowercased anyway unless case_sensitive=True is set.
    config_case_sensitive = Config(case_sensitive=True)
    res_ign = module_key("Foo", config_case_sensitive, ignore_case=True)
    res_no_ign = module_key("Foo", config_case_sensitive, ignore_case=False)
    assert res_ign == "Bfoo"
    assert res_no_ign == "BFoo"
    assert res_ign != res_no_ign

    # 3. sub_imports and order_by_type branches:
    # constants, classes, variables, isupper and len > 1, classes or first char isupper, else
    cfg_order = Config(
        order_by_type=True,
        constants=["const_item"],
        classes=["class_item"],
        variables=["var_item"],
    )

    # constant branch
    assert "A" in module_key("const_item", cfg_order, sub_imports=True)
    # class branch
    assert "B" in module_key("class_item", cfg_order, sub_imports=True)
    # variable branch
    assert "C" in module_key("var_item", cfg_order, sub_imports=True)
    # isupper and len > 1 branch
    assert "A" in module_key("UPPER", cfg_order, sub_imports=True)
    # classes or first char isupper branch (e.g. capitalized name not in classes explicitly)
    assert "B" in module_key("SomeClass", cfg_order, sub_imports=True)
    # else branch (lowercase, not in constants/classes/variables)
    assert "C" in module_key("otheritem", cfg_order, sub_imports=True)

    # 4. case_sensitive = False
    cfg_case_insensitive = Config(case_sensitive=False)
    res_ci = module_key("TestModule", cfg_case_insensitive)
    # should contain lowercase module name
    assert "testmodule" in res_ci

    # 5. length_sort branches:
    # length_sort = True
    cfg_len_sort = Config(length_sort=True)
    assert ":" in module_key("abc", cfg_len_sort)

    # length_sort_straight and straight_import = True
    cfg_len_straight = Config(length_sort_straight=True)
    assert ":" in module_key("abc", cfg_len_straight, straight_import=True)

    # section_name in length_sort_sections
    cfg_len_section = Config(length_sort_sections={"mysetsection"})
    assert ":" in module_key("abc", cfg_len_section, section_name="MySetSection")

    # 6. force_to_top branch ('A' vs 'B')
    cfg_force_top = Config(force_to_top=["top_module"])
    res_top = module_key("top_module", cfg_force_top)
    assert res_top.startswith("A")

    res_normal = module_key("normal_module", cfg_force_top)
    assert res_normal.startswith("B")
