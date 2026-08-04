# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

from isort.settings import Config
from isort.sorting import module_key


def test_module_key_comprehensive():
    # Test line 22-25: match with relative import (reverse_relative=True and False)
    config_rev = Config(reverse_relative=True)
    res1 = module_key(".foo", config_rev)
    assert "." in res1 or " " in res1

    config_normal_rel = Config(reverse_relative=False)
    res2 = module_key(".foo", config_normal_rel)
    assert "_" in res2

    # Test line 28-31: ignore_case True vs False
    # By default Config has case_sensitive=True, so ignore_case=True lowercases module_name
    # whereas ignore_case=False keeps "Foo". But wait, if case_sensitive=True,
    # module_name.lower() makes "Foo" -> "foo", and ignore_case=False keeps "Foo".
    # Wait, why did res_ignore == res_no_ignore? Because default config.case_sensitive is False in isort Config!
    # Let's override case_sensitive=True to see the difference, or check behavior properly.
    config_cs = Config(case_sensitive=True)
    res_ignore = module_key("Foo", config_cs, ignore_case=True)
    res_no_ignore = module_key("Foo", config_cs, ignore_case=False)
    assert res_ignore != res_no_ignore

    # Test lines 33-45: sub_imports and order_by_type branches
    # Constants match (prefix A)
    cfg_const = Config(order_by_type=True, constants=("CONST",))
    assert "A" in module_key("CONST", cfg_const, sub_imports=True)

    # Classes match (prefix B)
    cfg_class = Config(order_by_type=True, classes=("MyClass",))
    assert "B" in module_key("MyClass", cfg_class, sub_imports=True)

    # Variables match (prefix C)
    cfg_var = Config(order_by_type=True, variables=("var",))
    assert "C" in module_key("var", cfg_var, sub_imports=True)

    # isupper and len > 1 (prefix A)
    cfg_empty = Config(order_by_type=True)
    assert "A" in module_key("ABC", cfg_empty, sub_imports=True)

    # classes or first char is upper (prefix B)
    assert "B" in module_key("Somefunc", cfg_empty, sub_imports=True)

    # fallback else (prefix C)
    assert "C" in module_key("somefunc", cfg_empty, sub_imports=True)

    # Test line 46-47: case_sensitive = False
    cfg_insensitive = Config(case_sensitive=False)
    res_insens = module_key("ABC", cfg_insensitive)
    assert "abc" in res_insens

    # Test lines 49-52: length_sort branches
    # 1. config.length_sort = True
    cfg_len1 = Config(length_sort=True)
    assert ":" in module_key("foo", cfg_len1)

    # 2. config.length_sort_straight and straight_import
    cfg_len2 = Config(length_sort_straight=True)
    assert ":" in module_key("foo", cfg_len2, straight_import=True)

    # 3. str(section_name).lower() in config.length_sort_sections
    cfg_len3 = Config(length_sort_sections=("thirdparty",))
    assert ":" in module_key("foo", cfg_len3, section_name="ThirdParty")

    # Test line 55: force_to_top ('A' vs 'B')
    cfg_top = Config(force_to_top=("foo",))
    res_top = module_key("foo", cfg_top)
    assert res_top.startswith("A")

    res_not_top = module_key("bar", cfg_top)
    assert res_not_top.startswith("B")
