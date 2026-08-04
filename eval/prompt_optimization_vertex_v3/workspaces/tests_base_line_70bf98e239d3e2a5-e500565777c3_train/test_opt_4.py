# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

from isort.settings import Config
from isort.sorting import module_key

def test_module_key_comprehensive():
    # Test relative module with reverse_relative = True and False
    config_rev = Config(reverse_relative=True)
    res_rev = module_key(".foo", config_rev)
    assert res_rev is not None

    config_normal = Config(reverse_relative=False)
    res_norm = module_key(".foo", config_normal)
    assert res_norm is not None

    # Test ignore_case = True vs False
    config_ic = Config(case_sensitive=True)
    assert module_key("FOO", config_ic, ignore_case=True) is not None
    assert module_key("FOO", config_ic, ignore_case=False) is not None

    # Test sub_imports and order_by_type branches:
    # 1. module_name in constants
    cfg_order1 = Config(order_by_type=True, constants=("CONST",))
    assert "A" in module_key("CONST", cfg_order1, sub_imports=True)

    # 2. module_name in classes
    cfg_order2 = Config(order_by_type=True, classes=("MyClass",))
    assert "B" in module_key("MyClass", cfg_order2, sub_imports=True)

    # 3. module_name in variables
    cfg_order3 = Config(order_by_type=True, variables=("var",))
    assert "C" in module_key("var", cfg_order3, sub_imports=True)

    # 4. module_name.isupper() and len > 1
    cfg_order4 = Config(order_by_type=True)
    assert "A" in module_key("UPPER", cfg_order4, sub_imports=True)

    # 5. module_name starts with upper or in classes
    assert "B" in module_key("UpperName", cfg_order4, sub_imports=True)

    # 6. fallback to C (lowercase, not in constants/classes/variables)
    assert "C" in module_key("lowername", cfg_order4, sub_imports=True)

    # Test case_sensitive = False
    cfg_case = Config(case_sensitive=False)
    assert module_key("Foo", cfg_case) is not None

    # Test length_sort options:
    # length_sort = True
    cfg_len1 = Config(length_sort=True)
    assert module_key("foo", cfg_len1) is not None

    # length_sort_straight and straight_import = True
    cfg_len2 = Config(length_sort_straight=True)
    assert module_key("foo", cfg_len2, straight_import=True) is not None

    # section_name in length_sort_sections
    cfg_len3 = Config(length_sort_sections=("sec",))
    assert module_key("foo", cfg_len3, section_name="SEC") is not None

    # Test force_to_top (module in force_to_top results in 'A', otherwise 'B')
    cfg_top = Config(force_to_top=("top_mod",))
    assert module_key("top_mod", cfg_top).startswith("A")
    assert module_key("other_mod", cfg_top).startswith("B")
