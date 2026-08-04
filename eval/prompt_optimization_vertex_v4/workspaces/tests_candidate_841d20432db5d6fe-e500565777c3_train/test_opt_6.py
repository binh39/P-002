# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

import pytest
from isort.settings import Config
from isort.sorting import module_key

def test_module_key_full_coverage():
    # Test relative import regex matching and reverse_relative flag (True and False)
    config1 = Config(reverse_relative=True, case_sensitive=True)
    res1 = module_key(".foo", config1)
    assert res1.endswith(". foo")

    config2 = Config(reverse_relative=False, case_sensitive=True)
    res2 = module_key(".foo", config2)
    assert res2.endswith("._foo")

    # Test ignore_case = True vs False
    config3 = Config(case_sensitive=True, length_sort=True)
    assert module_key("FOO", config3, ignore_case=True) == "B3:foo"
    assert module_key("FOO", config3, ignore_case=False) == "B3:FOO"

    # Test sub_imports and order_by_type branches:
    # 1. module_name in config.constants -> prefix = "A"
    config_const = Config(constants=["const"], order_by_type=True, case_sensitive=True, length_sort=True)
    assert "A" in module_key("const", config_const, sub_imports=True)

    # 2. module_name in config.classes -> prefix = "B"
    config_cls = Config(classes=["MyClass"], order_by_type=True, case_sensitive=True, length_sort=True)
    assert "B" in module_key("MyClass", config_cls, sub_imports=True)

    # 3. module_name in config.variables -> prefix = "C"
    config_var = Config(variables=["var"], order_by_type=True, case_sensitive=True, length_sort=True)
    assert "C" in module_key("var", config_var, sub_imports=True)

    # 4. module_name.isupper() and len(module_name) > 1 -> prefix = "A"
    config_empty = Config(order_by_type=True, case_sensitive=True, length_sort=True)
    assert "A" in module_key("AB", config_empty, sub_imports=True)

    # 5. module_name in config.classes or module_name[0:1].isupper() -> prefix = "B"
    assert "B" in module_key("Abc", config_empty, sub_imports=True)

    # 6. fallback else -> prefix = "C"
    assert "C" in module_key("abc", config_empty, sub_imports=True)

    # Test case_sensitive = False
    config_insensitive = Config(case_sensitive=False, length_sort=True)
    assert module_key("ABC", config_insensitive) == "B3:abc"

    # Test length_sort combinations:
    # config.length_sort = True
    cfg_ls1 = Config(length_sort=True, case_sensitive=True)
    assert module_key("abc", cfg_ls1) == "B3:abc"

    # config.length_sort_straight and straight_import = True
    cfg_ls2 = Config(length_sort_straight=True, case_sensitive=True)
    assert module_key("abc", cfg_ls2, straight_import=True) == "B3:abc"

    # str(section_name).lower() in config.length_sort_sections
    cfg_ls3 = Config(length_sort_sections=("sec1",), case_sensitive=True)
    assert module_key("abc", cfg_ls3, section_name="SEC1") == "B3:abc"

    # Test force_to_top ('A' vs 'B' prefix at the very beginning)
    cfg_force = Config(force_to_top=["top"], case_sensitive=True, length_sort=True)
    assert module_key("top", cfg_force).startswith("A")
    assert module_key("other", cfg_force).startswith("B")
