# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

from isort.settings import Config
from isort.sorting import module_key


def test_module_key_all_branches():
    # 1. Relative import matching and reverse_relative = True
    config1 = Config(reverse_relative=True, case_sensitive=True)
    res1 = module_key(".foo", config1)
    assert res1.endswith("foo")

    # 2. Relative import matching and reverse_relative = False
    config2 = Config(reverse_relative=False, case_sensitive=True)
    res2 = module_key(".foo", config2)
    assert res2.endswith("foo")

    # 3. ignore_case = True
    config3 = Config(case_sensitive=True)
    res3 = module_key("FOO", config3, ignore_case=True)
    assert "foo" in res3

    # 4. sub_imports and order_by_type branches:
    # 4a. module_name in config.constants -> prefix 'A'
    config_order = Config(order_by_type=True, constants=["const"], case_sensitive=True)
    assert module_key("const", config_order, sub_imports=True).startswith("B")  # force_to_top is false -> 'B' + 'A' + ...

    # Let's test all order_by_type prefix branches explicitly:
    # constants -> 'A'
    cfg_const = Config(order_by_type=True, constants=["my_const"], case_sensitive=True)
    assert "A" in module_key("my_const", cfg_const, sub_imports=True)

    # classes -> 'B'
    cfg_class = Config(order_by_type=True, classes=["MyClass"], case_sensitive=True)
    assert "B" in module_key("MyClass", cfg_class, sub_imports=True)

    # variables -> 'C'
    cfg_var = Config(order_by_type=True, variables=["my_var"], case_sensitive=True)
    assert "C" in module_key("my_var", cfg_var, sub_imports=True)

    # isupper() and len > 1 -> 'A'
    cfg_isupper = Config(order_by_type=True, case_sensitive=True)
    res_isupper = module_key("ABC", cfg_isupper, sub_imports=True)
    # Prefix 'A' should be right after force_to_top ('B')
    assert res_isupper.startswith("BA")

    # classes or module_name[0:1].isupper() -> 'B'
    cfg_upper_char = Config(order_by_type=True, case_sensitive=True)
    res_upper_char = module_key("Abc", cfg_upper_char, sub_imports=True)
    assert res_upper_char.startswith("BB")

    # fallback else -> 'C'
    cfg_fallback = Config(order_by_type=True, case_sensitive=True)
    res_fallback = module_key("abc", cfg_fallback, sub_imports=True)
    assert res_fallback.startswith("BC")

    # 5. case_sensitive = False
    cfg_case_sens = Config(case_sensitive=False)
    assert "foo" in module_key("FOO", cfg_case_sens)

    # 6. length_sort branches:
    # length_sort = True via config.length_sort
    cfg_len1 = Config(length_sort=True, case_sensitive=True)
    assert ":" in module_key("foo", cfg_len1)

    # length_sort = True via length_sort_straight and straight_import
    cfg_len2 = Config(length_sort_straight=True, case_sensitive=True)
    assert ":" in module_key("foo", cfg_len2, straight_import=True)

    # length_sort = True via section_name in length_sort_sections
    cfg_len3 = Config(length_sort_sections={"thirdparty"}, case_sensitive=True)
    assert ":" in module_key("foo", cfg_len3, section_name="THIRDPARTY")

    # length_sort = False
    cfg_len_false = Config(length_sort=False, length_sort_straight=False, case_sensitive=True)
    assert ":" not in module_key("foo", cfg_len_false)

    # 7. force_to_top branches:
    # module_name in force_to_top -> 'A'
    cfg_top_true = Config(force_to_top=["foo"], case_sensitive=True)
    assert module_key("foo", cfg_top_true).startswith("A")

    # module_name not in force_to_top -> 'B'
    cfg_top_false = Config(force_to_top=[], case_sensitive=True)
    assert module_key("foo", cfg_top_false).startswith("B")
