# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

from isort.settings import Config
from isort.sorting import module_key


def test_module_key_comprehensive():
    # Test relative module with reverse_relative = True and False
    config_rev = Config(reverse_relative=True)
    res_rev = module_key(".foo", config_rev)
    assert res_rev == "B_.foo" or "." in res_rev

    config_normal_rel = Config(reverse_relative=False)
    res_norm = module_key(".foo", config_normal_rel)
    assert res_norm is not None

    # Test ignore_case True vs False
    config_ic = Config(case_sensitive=True)
    res_ic_true = module_key("Foo", config_ic, ignore_case=True)
    res_ic_false = module_key("Foo", config_ic, ignore_case=False)
    assert res_ic_true != res_ic_false

    # Test sub_imports and order_by_type branching
    # Constants
    cfg_order = Config(order_by_type=True, constants=["myconst"])
    assert module_key("myconst", cfg_order, sub_imports=True) is not None

    # Classes
    cfg_order_cls = Config(order_by_type=True, classes=["MyClass"])
    assert module_key("MyClass", cfg_order_cls, sub_imports=True) is not None

    # Variables
    cfg_order_var = Config(order_by_type=True, variables=["myvar"])
    assert module_key("myvar", cfg_order_var, sub_imports=True) is not None

    # Isupper and len > 1
    cfg_order_upper = Config(order_by_type=True)
    assert module_key("ABC", cfg_order_upper, sub_imports=True) is not None

    # Classes or first letter isupper
    cfg_order_first_upper = Config(order_by_type=True, classes=[])
    assert module_key("Abc", cfg_order_first_upper, sub_imports=True) is not None

    # Fallback to 'C'
    cfg_order_fallback = Config(order_by_type=True)
    assert module_key("abc", cfg_order_fallback, sub_imports=True) is not None

    # case_sensitive = False
    cfg_insensitive = Config(case_sensitive=False)
    assert module_key("ABC", cfg_insensitive) is not None

    # length_sort variations
    cfg_len1 = Config(length_sort=True)
    assert module_key("foo", cfg_len1) is not None

    cfg_len2 = Config(length_sort_straight=True)
    assert module_key("foo", cfg_len2, straight_import=True) is not None

    cfg_len3 = Config(length_sort_sections=["sec1"])
    assert module_key("foo", cfg_len3, section_name="SEC1") is not None

    # force_to_top
    cfg_top = Config(force_to_top=["topmod"])
    assert module_key("topmod", cfg_top).startswith("A")
    assert module_key("other", cfg_top).startswith("B")
