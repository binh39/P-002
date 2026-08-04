# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47]]}

from isort.settings import Config
from isort.sorting import module_key


def test_module_key_comprehensive():
    # Test cases to cover all branches and paths in module_key:
    # 1. relative import with reverse_relative = True and False
    # 2. ignore_case = True and False
    # 3. sub_imports = True and order_by_type = True testing constants, classes, variables, isupper len > 1, first char upper, else (prefix A, B, C)
    # 4. case_sensitive = True and False
    # 5. length_sort combinations: length_sort, length_sort_straight + straight_import, length_sort_sections + section_name
    # 6. force_to_top presence (True -> 'A', False -> 'B')

    # Config 1: Default-like config
    config = Config()

    # Basic module name without relative prefix
    key1 = module_key("os", config)
    assert isinstance(key1, str)

    # Relative import with reverse_relative=False (default)
    config_rel = Config(reverse_relative=False)
    key_rel1 = module_key(".os", config_rel)
    assert "_" in key_rel1

    # Relative import with reverse_relative=True
    config_rev = Config(reverse_relative=True)
    key_rev = module_key(".os", config_rev)
    assert " " in key_rev

    # ignore_case = True
    key_ignore = module_key("OS", config, ignore_case=True)
    assert "os" in key_ignore

    # sub_imports and order_by_type branches:
    # We populate config fields to trigger different prefixes: A, B, C
    # config.constants, config.classes, config.variables
    custom_config = Config(
        order_by_type=True,
        constants=["const_val"],
        classes=["class_val"],
        variables=["var_val"],
        force_to_top=["forced_mod"],
        case_sensitive=False,
    )

    # constants -> prefix A
    key_const = module_key("const_val", custom_config, sub_imports=True)
    assert key_const.startswith("BA") or key_const.startswith("AA")

    # classes -> prefix B
    key_class = module_key("class_val", custom_config, sub_imports=True)
    assert "B" in key_class

    # variables -> prefix C
    key_var = module_key("var_val", custom_config, sub_imports=True)
    assert "C" in key_var

    # isupper() and len > 1 -> prefix A
    key_upper = module_key("MYCONST", custom_config, sub_imports=True)
    assert "A" in key_upper

    # module_name[0:1].isupper() -> prefix B
    key_title = module_key("MyClass", custom_config, sub_imports=True)
    assert "B" in key_title

    # else -> prefix C
    key_else = module_key("other_func", custom_config, sub_imports=True)
    assert "C" in key_else

    # force_to_top -> 'A'
    key_forced = module_key("forced_mod", custom_config)
    assert key_forced.startswith("A")

    # length_sort config options:
    # 1. config.length_sort = True
    cfg_ls1 = Config(length_sort=True)
    assert ":" in module_key("os", cfg_ls1)

    # 2. config.length_sort_straight = True and straight_import = True
    cfg_ls2 = Config(length_sort_straight=True)
    assert ":" in module_key("os", cfg_ls2, straight_import=True)

    # 3. section_name in length_sort_sections
    cfg_ls3 = Config(length_sort_sections=["thirdparty"])
    assert ":" in module_key("os", cfg_ls3, section_name="ThirdParty")
