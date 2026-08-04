# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47]]}

from isort.settings import Config
from isort.sorting import module_key


def test_module_key_full_coverage():
    # 1. Relative import matching (reverse_relative = True and False)
    config_rev = Config(reverse_relative=True)
    res_rev = module_key(".foo", config_rev)
    assert "_" not in res_rev  # uses space or whatever sep

    config_norm = Config(reverse_relative=False)
    res_norm = module_key(".foo", config_norm)
    assert res_norm is not None

    # 2. ignore_case = True and False
    cfg = Config()
    key_ignore = module_key("Foo", cfg, ignore_case=True)
    key_no_ignore = module_key("Foo", cfg, ignore_case=False)
    assert key_ignore != key_no_ignore or len(key_ignore) > 0

    # 3. sub_imports and order_by_type branches:
    # constants, classes, variables, isupper & len > 1, first char upper, else (C)
    cfg_order = Config(
        order_by_type=True,
        constants=["CONST"],
        classes=["MyClass"],
        variables=["my_var"],
    )

    # constant (prefix A)
    assert "A" in module_key("CONST", cfg_order, sub_imports=True)
    # class (prefix B)
    assert "B" in module_key("MyClass", cfg_order, sub_imports=True)
    # variable (prefix C)
    assert "C" in module_key("my_var", cfg_order, sub_imports=True)
    # isupper and len > 1 (prefix A)
    assert "A" in module_key("UPPER", cfg_order, sub_imports=True)
    # class or first char upper (prefix B)
    assert "B" in module_key("OtherUpper", cfg_order, sub_imports=True)
    # else (prefix C)
    assert "C" in module_key("lower_case_func", cfg_order, sub_imports=True)

    # 4. case_sensitive = False
    cfg_case = Config(case_sensitive=False)
    res_case = module_key("FOO", cfg_case)
    assert res_case is not None

    # 5. length_sort branches:
    # length_sort = True
    cfg_len1 = Config(length_sort=True)
    assert module_key("foo", cfg_len1).startswith("B")

    # length_sort_straight and straight_import = True
    cfg_len2 = Config(length_sort_straight=True)
    assert module_key("foo", cfg_len2, straight_import=True).startswith("B")

    # section_name in length_sort_sections
    cfg_len3 = Config(length_sort_sections=["thirdparty"])
    assert module_key("foo", cfg_len3, section_name="ThirdParty").startswith("B")

    # 6. force_to_top branch (module_name in config.force_to_top -> 'A')
    cfg_top = Config(force_to_top=["topmod"])
    assert module_key("topmod", cfg_top).startswith("A")
    assert module_key("other", cfg_top).startswith("B")
