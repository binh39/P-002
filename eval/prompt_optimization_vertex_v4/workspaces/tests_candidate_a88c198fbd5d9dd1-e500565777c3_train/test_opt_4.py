# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

import pytest
from isort.sorting import module_key
from isort.settings import Config


def test_module_key_comprehensive():
    # Test relative module with reverse_relative = True and False
    config_rev = Config(reverse_relative=True, case_sensitive=True)
    res_rev = module_key(".foo", config_rev)
    assert res_rev.endswith(". foo") or "." in res_rev

    config_no_rev = Config(reverse_relative=False, case_sensitive=True)
    res_no_rev = module_key(".foo", config_no_rev)
    assert res_no_rev.endswith("._foo")

    # Test ignore_case = True vs False
    config_ignore = Config(case_sensitive=True)
    res_ignore = module_key("FOO", config_ignore, ignore_case=True)
    res_no_ignore = module_key("FOO", config_ignore, ignore_case=False)
    assert res_ignore != res_no_ignore

    # Test sub_imports and order_by_type with constants, classes, variables, isupper > 1, etc.
    config_order = Config(
        order_by_type=True,
        constants=["const_item"],
        classes=["class_item", "ClassUpper"],
        variables=["var_item"],
        case_sensitive=True,
    )

    # 1. module_name in config.constants -> prefix = "A"
    assert "A" in module_key("const_item", config_order, sub_imports=True)

    # 2. module_name in config.classes -> prefix = "B"
    assert "B" in module_key("class_item", config_order, sub_imports=True)

    # 3. module_name in config.variables -> prefix = "C"
    assert "C" in module_key("var_item", config_order, sub_imports=True)

    # 4. module_name.isupper() and len(module_name) > 1 -> prefix = "A"
    assert "A" in module_key("UPPER", config_order, sub_imports=True)

    # 5. module_name in config.classes or module_name[0:1].isupper() -> prefix = "B"
    assert "B" in module_key("Upperitem", config_order, sub_imports=True)

    # 6. Fallback -> prefix = "C"
    assert "C" in module_key("loweritem", config_order, sub_imports=True)

    # Test case_sensitive = False
    config_insensitive = Config(case_sensitive=False)
    res_insens = module_key("Foo", config_insensitive)
    assert res_insens == "Bfoo"

    # Test length_sort variations:
    # - length_sort = True
    config_len_sort = Config(length_sort=True, case_sensitive=True)
    assert ":" in module_key("foo", config_len_sort)

    # - length_sort_straight and straight_import = True
    config_len_straight = Config(length_sort_straight=True, case_sensitive=True)
    assert ":" in module_key("foo", config_len_straight, straight_import=True)

    # - section_name in length_sort_sections
    config_sec_sort = Config(length_sort_sections={"thirdparty"}, case_sensitive=True)
    assert ":" in module_key("foo", config_sec_sort, section_name="ThirdParty")

    # Test force_to_top ('A' vs 'B' prefix)
    config_force = Config(force_to_top=["top_module"], case_sensitive=True)
    assert module_key("top_module", config_force).startswith("A")
    assert module_key("other_module", config_force).startswith("B")
