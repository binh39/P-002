# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47]]}

from isort.sorting import module_key
from isort.settings import Config


def test_module_key_comprehensive():
    # Test relative import with reverse_relative = True
    config_rev = Config(reverse_relative=True)
    res = module_key(".os", config_rev)
    assert "." in res or "_" in res or " " in res

    # Test relative import with reverse_relative = False (default)
    config_norm = Config(reverse_relative=False)
    res2 = module_key("..os", config_norm)
    assert res2 is not None

    # Test ignore_case parameter (passed as a function argument, not in Config)
    config_ic = Config()
    res_ic = module_key("OS", config_ic, ignore_case=True)
    assert res_ic is not None

    # Test sub_imports and order_by_type branches
    # Constants branch
    config_const = Config(order_by_type=True, constants=["my_const"])
    assert "A" in module_key("my_const", config_const, sub_imports=True)

    # Classes branch
    config_class = Config(order_by_type=True, classes=["MyClass"])
    assert "B" in module_key("MyClass", config_class, sub_imports=True)

    # Variables branch
    config_var = Config(order_by_type=True, variables=["my_var"])
    assert "C" in module_key("my_var", config_var, sub_imports=True)

    # isupper and len > 1 branch
    config_upper = Config(order_by_type=True)
    assert "A" in module_key("ABC", config_upper, sub_imports=True)

    # module_name in config.classes or module_name[0:1].isupper() branch
    config_title = Config(order_by_type=True)
    assert "B" in module_key("SomeName", config_title, sub_imports=True)

    # Else branch for prefix (lowercase, not in constants/classes/variables)
    config_else = Config(order_by_type=True)
    assert "C" in module_key("lowercase_thing", config_else, sub_imports=True)

    # case_sensitive = False
    config_cs_false = Config(case_sensitive=False)
    assert module_key("OS", config_cs_false) == module_key("os", config_cs_false)

    # length_sort branches
    # 1. config.length_sort = True
    config_len1 = Config(length_sort=True)
    assert ":" in module_key("os", config_len1)

    # 2. config.length_sort_straight = True and straight_import = True
    config_len2 = Config(length_sort_straight=True)
    assert ":" in module_key("os", config_len2, straight_import=True)

    # 3. str(section_name).lower() in config.length_sort_sections
    config_len3 = Config(length_sort_sections=["thirdparty"])
    assert ":" in module_key("os", config_len3, section_name="THIRDPARTY")

    # force_to_top check
    config_top = Config(force_to_top=["top_mod"])
    assert module_key("top_mod", config_top).startswith("A")
    assert module_key("other_mod", config_top).startswith("B")
