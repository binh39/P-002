# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

from isort.sorting import module_key
from isort.settings import Config


def test_module_key_comprehensive():
    # Test relative module matching with reverse_relative = True and False
    config_rev = Config(reverse_relative=True)
    res_rev = module_key(".foo", config_rev)
    assert "." in res_rev or " " in res_rev

    config_normal = Config(reverse_relative=False)
    res_normal = module_key(".foo", config_normal)
    assert "_" in res_normal

    # Test ignore_case = True vs False
    config_sensitive = Config(case_sensitive=True)
    key_ignore_sens = module_key("FOO", config_sensitive, ignore_case=True)
    key_no_ignore_sens = module_key("FOO", config_sensitive, ignore_case=False)
    assert key_ignore_sens != key_no_ignore_sens

    # Test sub_imports and order_by_type branches via Config initialization arguments:
    # 1. module_name in config.constants -> prefix 'A'
    config_const = Config(order_by_type=True, constants=("const",))
    assert module_key("const", config_const, sub_imports=True).startswith("BA")

    # 2. module_name in config.classes -> prefix 'B'
    config_class = Config(order_by_type=True, classes=("cls",))
    assert module_key("cls", config_class, sub_imports=True).startswith("BB")

    # 3. module_name in config.variables -> prefix 'C'
    config_var = Config(order_by_type=True, variables=("var",))
    assert module_key("var", config_var, sub_imports=True).startswith("BC")

    # 4. module_name.isupper() and len(module_name) > 1 -> prefix 'A'
    config_order = Config(order_by_type=True)
    assert module_key("UPPER", config_order, sub_imports=True).startswith("BA")

    # 5. module_name in config.classes or module_name[0:1].isupper() -> prefix 'B'
    assert module_key("Upper", config_order, sub_imports=True).startswith("BB")

    # 6. Else branch -> prefix 'C'
    assert module_key("lower", config_order, sub_imports=True).startswith("BC")

    # Test case_sensitive = False
    config_insensitive = Config(case_sensitive=False)
    assert module_key("TestModule", config_insensitive) == module_key("testmodule", config_insensitive)

    # Test length_sort combinations:
    # - config.length_sort = True
    config_ls1 = Config(length_sort=True)
    assert ":" in module_key("abc", config_ls1)

    # - config.length_sort_straight = True and straight_import = True
    config_ls2 = Config(length_sort_straight=True)
    assert ":" in module_key("abc", config_ls2, straight_import=True)

    # - str(section_name).lower() in config.length_sort_sections
    config_ls3 = Config(length_sort_sections=("sec",))
    assert ":" in module_key("abc", config_ls3, section_name="SEC")

    # Test force_to_top ('A' vs 'B' prefix)
    config_top = Config(force_to_top=("top_mod",))
    assert module_key("top_mod", config_top).startswith("A")
    assert module_key("other_mod", config_top).startswith("B")
