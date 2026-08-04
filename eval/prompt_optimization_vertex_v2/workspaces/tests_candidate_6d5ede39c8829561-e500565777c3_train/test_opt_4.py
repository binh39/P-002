# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

from isort.settings import Config
from isort.sorting import module_key


def test_module_key_comprehensive():
    # 1. Relative import matching (reverse_relative = True and False)
    config_rev = Config(reverse_relative=True)
    res_rev = module_key(".os", config_rev)
    assert "." in res_rev or " " in res_rev

    config_normal_rel = Config(reverse_relative=False)
    res_normal_rel = module_key(".os", config_normal_rel)
    assert "_" in res_normal_rel

    # 2. ignore_case parameter vs Config
    config_ic = Config(case_sensitive=True)
    res_ic = module_key("OS", config_ic, ignore_case=True)

    config_no_ic = Config(case_sensitive=True)
    res_no_ic = module_key("OS", config_no_ic, ignore_case=False)
    assert res_ic != res_no_ic

    # 3. sub_imports and order_by_type branches:
    # constants, classes, variables, isupper len>1, classes/isupper[0:1], else
    config_order = Config(
        order_by_type=True,
        constants=frozenset(["const_item"]),
        classes=frozenset(["class_item"]),
        variables=frozenset(["var_item"]),
    )

    # constants match
    assert "A" in module_key("const_item", config_order, sub_imports=True)
    # classes match
    assert "B" in module_key("class_item", config_order, sub_imports=True)
    # variables match
    assert "C" in module_key("var_item", config_order, sub_imports=True)
    # isupper and len > 1
    assert "A" in module_key("UPPER", config_order, sub_imports=True)
    # in classes or first letter isupper
    assert "B" in module_key("Upperfirst", config_order, sub_imports=True)
    # else branch (lowercase, not in any list)
    assert "C" in module_key("lower_other", config_order, sub_imports=True)

    # 4. case_sensitive = False branch
    config_insensitive = Config(case_sensitive=False)
    res_insens = module_key("OS", config_insensitive)
    assert "os" in res_insens

    # 5. length_sort branches:
    # length_sort=True
    cfg_len1 = Config(length_sort=True)
    assert ":" in module_key("os", cfg_len1)

    # length_sort_straight=True and straight_import=True
    cfg_len2 = Config(length_sort_straight=True)
    assert ":" in module_key("os", cfg_len2, straight_import=True)

    # section_name in length_sort_sections
    cfg_len3 = Config(length_sort_sections=("thirdparty",))
    assert ":" in module_key("os", cfg_len3, section_name="THIRDPARTY")

    # 6. force_to_top branch (module_name in config.force_to_top -> 'A', else 'B')
    cfg_top = Config(force_to_top=("top_mod",))
    assert module_key("top_mod", cfg_top).startswith("A")
    assert module_key("other_mod", cfg_top).startswith("B")
