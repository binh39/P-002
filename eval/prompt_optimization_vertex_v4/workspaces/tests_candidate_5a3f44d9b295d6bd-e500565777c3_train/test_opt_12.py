# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

from isort.settings import Config
from isort.sorting import module_key


def test_module_key_comprehensive():
    # Test cases to cover all branches and lines of module_key in isort/sorting.py

    # 1. Relative import matching (reverse_relative=True and False)
    config_rev = Config(reverse_relative=True)
    key_rev = module_key(".foo", config_rev)
    assert key_rev.startswith("B")  # B prefix, length_sort=False -> module_name becomes ". foo"

    config_normal_rel = Config(reverse_relative=False)
    key_norm_rel = module_key(".foo", config_normal_rel)
    assert "._foo" in key_norm_rel

    # 2. ignore_case = True vs False
    config = Config()
    key_ignore = module_key("Foo", config, ignore_case=True)
    config_case_sens = Config(case_sensitive=True)
    key_no_ignore = module_key("FOO", config_case_sens, ignore_case=False)
    assert key_ignore != key_no_ignore

    # 3. sub_imports and order_by_type branches:
    # constants, classes, variables, isupper len > 1, classes/isupper first char, else (C)
    config_order = Config(
        order_by_type=True,
        constants=["CONST"],
        classes=["MyClass"],
        variables=["var"],
    )

    # constant (A)
    k_const = module_key("CONST", config_order, sub_imports=True)
    assert "A" in k_const

    # classes (B)
    k_class = module_key("MyClass", config_order, sub_imports=True)
    assert "B" in k_class

    # variables (C)
    k_var = module_key("var", config_order, sub_imports=True)
    assert "C" in k_var

    # isupper() and len > 1 -> A
    k_isupper = module_key("ABC", config_order, sub_imports=True)
    assert "A" in k_isupper

    # in classes or module_name[0:1].isupper() -> B
    k_upper_char = module_key("Somefunc", config_order, sub_imports=True)
    assert "B" in k_upper_char

    # else -> C
    k_else = module_key("lowerfunc", config_order, sub_imports=True)
    assert "C" in k_else

    # 4. case_sensitive = False
    config_case = Config(case_sensitive=False)
    k_insensitive = module_key("Foo", config_case)
    assert "foo" in k_insensitive

    # 5. length_sort branches:
    # config.length_sort = True
    config_len1 = Config(length_sort=True)
    k_len1 = module_key("foo", config_len1)
    assert ":" in k_len1

    # config.length_sort_straight and straight_import = True
    config_len2 = Config(length_sort_straight=True)
    k_len2 = module_key("foo", config_len2, straight_import=True)
    assert ":" in k_len2

    # str(section_name).lower() in config.length_sort_sections
    config_len3 = Config(length_sort_sections={"sec"})
    k_len3 = module_key("foo", config_len3, section_name="SEC")
    assert ":" in k_len3

    # 6. force_to_top branch (module_name in config.force_to_top -> 'A' else 'B')
    config_top = Config(force_to_top=["topmod"])
    k_top = module_key("topmod", config_top)
    assert k_top.startswith("A")

    k_not_top = module_key("othermod", config_top)
    assert k_not_top.startswith("B")
