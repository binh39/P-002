# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

from isort.settings import Config
from isort.sorting import module_key


def test_module_key_all_branches():
    # 1. Test relative import with reverse_relative = True and False
    config_rev = Config(reverse_relative=True)
    res_rev = module_key(".foo", config_rev)
    assert res_rev.startswith("B")

    config_norm = Config(reverse_relative=False)
    res_norm = module_key(". foo", config_norm)
    assert res_norm.startswith("B")

    # 2. Test ignore_case = True vs False
    config_default = Config(case_sensitive=True)
    key_ignore = module_key("FOO", config_default, ignore_case=True)
    key_no_ignore = module_key("FOO", config_default, ignore_case=False)
    assert key_ignore != key_no_ignore

    # 3. Test sub_imports and order_by_type branches:
    # constants, classes, variables, uppercase (>1 len), upper initial letter, else (lowercase/other)
    config_order = Config(order_by_type=True, constants=("CONST",), classes=("ClassA",), variables=("var",))

    # constants match
    assert "A" in module_key("CONST", config_order, sub_imports=True)
    # classes match
    assert "B" in module_key("ClassA", config_order, sub_imports=True)
    # variables match
    assert "C" in module_key("var", config_order, sub_imports=True)
    # isupper and len > 1
    assert "A" in module_key("UPPER", config_order, sub_imports=True)
    # in config.classes or module_name[0:1].isupper()
    assert "B" in module_key("Something", config_order, sub_imports=True)
    # else branch (lowercase, not in constants/classes/variables)
    assert "C" in module_key("lowercase", config_order, sub_imports=True)

    # 4. Test case_sensitive = False
    config_insensitive = Config(case_sensitive=False)
    k1 = module_key("Module", config_insensitive)
    k2 = module_key("module", config_insensitive)
    assert k1 == k2

    # 5. Test length_sort combinations:
    # config.length_sort
    config_ls = Config(length_sort=True)
    assert ":" in module_key("foo", config_ls)

    # config.length_sort_straight and straight_import
    config_lss = Config(length_sort_straight=True)
    assert ":" in module_key("foo", config_lss, straight_import=True)

    # str(section_name).lower() in config.length_sort_sections
    config_lsssec = Config(length_sort_sections=("third_party",))
    assert ":" in module_key("foo", config_lsssec, section_name="THIRD_PARTY")

    # 6. Test force_to_top inclusion ('A' vs 'B' prefix at the very start)
    config_top = Config(force_to_top=("forced",))
    key_top = module_key("forced", config_top)
    key_not_top = module_key("normal", config_top)
    assert key_top.startswith("A")
    assert key_not_top.startswith("B")
