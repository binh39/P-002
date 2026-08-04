# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

import pytest
from isort.sorting import module_key
from isort.settings import Config


def test_module_key_comprehensive():
    # Test relative imports with reverse_relative = True and False
    config_default = Config()
    
    # 1. match (relative import), reverse_relative = False (default)
    res1 = module_key(".foo", config_default)
    assert res1.startswith("B")

    config_reverse = Config(reverse_relative=True)
    res2 = module_key(".foo", config_reverse)
    assert res2.startswith("B")

    # 2. ignore_case = True vs False
    config_sensitive = Config(case_sensitive=True)
    res_ignore = module_key("Foo", config_sensitive, ignore_case=True)
    res_no_ignore = module_key("Foo", config_sensitive, ignore_case=False)
    assert res_ignore != res_no_ignore

    # 3. sub_imports and config.order_by_type branching
    # Constants branch
    cfg_order_const = Config(order_by_type=True, constants=("my_const",), case_sensitive=True)
    assert "A" in module_key("my_const", cfg_order_const, sub_imports=True)

    # Classes branch
    cfg_order_classes = Config(order_by_type=True, classes=("MyClass",), case_sensitive=True)
    assert "B" in module_key("MyClass", cfg_order_classes, sub_imports=True)

    # Variables branch
    cfg_order_vars = Config(order_by_type=True, variables=("my_var",), case_sensitive=True)
    assert "C" in module_key("my_var", cfg_order_vars, sub_imports=True)

    # isupper() and len > 1 branch
    cfg_order_default = Config(order_by_type=True, case_sensitive=True)
    assert "A" in module_key("ABC", cfg_order_default, sub_imports=True)

    # in classes or first char isupper branch
    assert "B" in module_key("Someclass", cfg_order_default, sub_imports=True)

    # Fallback to C (lowercase, not in constants/classes/variables)
    assert "C" in module_key("lowerstuff", cfg_order_default, sub_imports=True)

    # 4. case_sensitive = False
    cfg_case = Config(case_sensitive=False)
    res_case = module_key("FOO", cfg_case)
    assert "foo" in res_case

    # 5. length_sort branches
    # length_sort = True
    cfg_len1 = Config(length_sort=True)
    assert ":" in module_key("foo", cfg_len1)

    # length_sort_straight and straight_import = True
    cfg_len2 = Config(length_sort_straight=True)
    assert ":" in module_key("foo", cfg_len2, straight_import=True)

    # section_name in length_sort_sections
    cfg_len3 = Config(length_sort_sections=("sec",))
    assert ":" in module_key("foo", cfg_len3, section_name="SEC")

    # 6. force_to_top ('A' vs 'B' prefix at the very beginning)
    cfg_top = Config(force_to_top=("topmod",))
    assert module_key("topmod", cfg_top).startswith("A")
    assert module_key("othermod", cfg_top).startswith("B")
