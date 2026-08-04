# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47]]}

from isort.settings import Config
from isort.sorting import module_key


def test_module_key_comprehensive():
    # 1. Relative import matching (reverse_relative = True and False)
    config_rev = Config(reverse_relative=True)
    res_rev = module_key(".foo", config_rev)
    assert "." in res_rev or " " in res_rev

    config_norm_rel = Config(reverse_relative=False)
    res_norm_rel = module_key(".foo", config_norm_rel)
    assert "_" in res_norm_rel

    # 2. ignore_case True vs False
    config_default = Config()
    res_ignore = module_key("FOO", config_default, ignore_case=True)
    res_no_ignore = module_key("FOO", config_default, ignore_case=False)
    # When case_sensitive is False by default (or depending on config), let's check values directly or use different casing
    res_ignore_diff = module_key("Foo", config_default, ignore_case=True)
    res_no_ignore_diff = module_key("Foo", config_default, ignore_case=False)
    assert res_ignore_diff != res_no_ignore_diff or res_ignore == "Bfoo"

    # 3. sub_imports and order_by_type branches:
    # constants, classes, variables, isupper and len > 1, classes/isupper first char, else
    config_order = Config(order_by_type=True, constants=("CONST",), classes=("ClassA",), variables=("var",))

    # constants ('A')
    assert "A" in module_key("CONST", config_order, sub_imports=True)
    # classes ('B')
    assert "B" in module_key("ClassA", config_order, sub_imports=True)
    # variables ('C')
    assert "C" in module_key("var", config_order, sub_imports=True)
    # isupper() and len > 1 ('A')
    assert "A" in module_key("UPPER", config_order, sub_imports=True)
    # first char is upper or in classes ('B')
    assert "B" in module_key("Titlecase", config_order, sub_imports=True)
    # else ('C')
    assert "C" in module_key("lowercase", config_order, sub_imports=True)

    # 4. case_sensitive = False
    config_insensitive = Config(case_sensitive=False)
    res_ci = module_key("ABC", config_insensitive)
    assert "abc" in res_ci

    # 5. length_sort branches:
    # config.length_sort
    config_ls1 = Config(length_sort=True)
    assert ":" in module_key("abc", config_ls1)

    # config.length_sort_straight and straight_import
    config_ls2 = Config(length_sort_straight=True)
    assert ":" in module_key("abc", config_ls2, straight_import=True)

    # str(section_name).lower() in config.length_sort_sections
    config_ls3 = Config(length_sort_sections=("sec1",))
    assert ":" in module_key("abc", config_ls3, section_name="SEC1")

    # 6. force_to_top ('A' vs 'B' prefix based on presence in force_to_top)
    config_top = Config(force_to_top=("top_module",))
    key_top = module_key("top_module", config_top)
    key_not_top = module_key("other_module", config_top)
    assert key_top.startswith("A")
    assert key_not_top.startswith("B")
