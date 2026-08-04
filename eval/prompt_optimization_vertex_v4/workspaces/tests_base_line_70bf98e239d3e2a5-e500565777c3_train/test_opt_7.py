# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

import pytest
from isort.settings import Config
from isort.sorting import module_key

def test_module_key_coverage():
    # 1. Test relative module name with reverse_relative = True and False
    config1 = Config(reverse_relative=True, order_by_type=False, case_sensitive=True)
    res1 = module_key(".foo", config1)
    assert "." in res1 or " " in res1
    
    config1_rev = Config(reverse_relative=False, order_by_type=False, case_sensitive=True)
    res1_rev = module_key(".foo", config1_rev)
    assert "_" in res1_rev

    # 2. Test ignore_case parameter passed into module_key (ignoring config since ignore_case is not a Config setting)
    config_default = Config(case_sensitive=True)
    res_ignore = module_key("FOO", config_default, ignore_case=True)
    res_no_ignore = module_key("FOO", config_default, ignore_case=False)
    assert res_ignore != res_no_ignore

    # 3. Test sub_imports and order_by_type branches:
    # constants, classes, variables, isupper and len > 1, first char upper or in classes, else (C)
    config_order = Config(
        order_by_type=True,
        constants=frozenset(["const"]),
        classes=frozenset(["MyClass"]),
        variables=frozenset(["var"]),
    )
    # constants -> prefix 'A'
    assert "A" in module_key("const", config_order, sub_imports=True)
    # classes -> prefix 'B'
    assert "B" in module_key("MyClass", config_order, sub_imports=True)
    # variables -> prefix 'C'
    assert "C" in module_key("var", config_order, sub_imports=True)
    # isupper and len > 1 -> prefix 'A'
    assert "A" in module_key("ABC", config_order, sub_imports=True)
    # first char upper -> prefix 'B'
    assert "B" in module_key("Someother", config_order, sub_imports=True)
    # else -> prefix 'C'
    assert "C" in module_key("lowercase", config_order, sub_imports=True)

    # 4. Test case_sensitive = False
    config_insensitive = Config(case_sensitive=False)
    res_insensitive = module_key("Foo", config_insensitive)
    assert res_insensitive.endswith("foo")

    # 5. Test length_sort combinations:
    # length_sort = True
    config_ls1 = Config(length_sort=True)
    assert ":" in module_key("foo", config_ls1)

    # length_sort_straight and straight_import = True
    config_ls2 = Config(length_sort_straight=True)
    assert ":" in module_key("foo", config_ls2, straight_import=True)

    # section_name in length_sort_sections
    config_ls3 = Config(length_sort_sections=frozenset(["myset"]))
    assert ":" in module_key("foo", config_ls3, section_name="MYSET")

    # 6. Test force_to_top branch ('A' vs 'B')
    config_top = Config(force_to_top=("topmod",))
    res_top = module_key("topmod", config_top)
    assert res_top.startswith("A")

    res_not_top = module_key("othermod", config_top)
    assert res_not_top.startswith("B")
