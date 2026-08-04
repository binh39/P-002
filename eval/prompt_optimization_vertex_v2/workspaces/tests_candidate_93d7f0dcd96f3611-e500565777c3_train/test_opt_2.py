# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

from isort.settings import Config
from isort.sorting import module_key


def test_module_key_comprehensive():
    # 1. Relative import with reverse_relative = True and False
    config_rev = Config(reverse_relative=True, case_sensitive=True)
    res_rev = module_key(".os", config_rev)
    assert res_rev.endswith(".os") or "." in res_rev

    config_no_rev = Config(reverse_relative=False, case_sensitive=True)
    res_no_rev = module_key(".os", config_no_rev)
    assert "_" in res_no_rev

    # 2. ignore_case = True vs False
    config_ignore = Config(case_sensitive=True)
    res_ignore = module_key("OS", config_ignore, ignore_case=True)
    assert res_ignore.endswith("os")

    res_no_ignore = Config(case_sensitive=True)
    res_no_ignore_val = module_key("OS", res_no_ignore, ignore_case=False)
    assert res_no_ignore_val.endswith("OS")

    # 3. sub_imports and order_by_type branches:
    # constants, classes, variables, isupper() > 1, classes/isupper first char, else (C)
    config_order = Config(
        order_by_type=True,
        constants=["CONST"],
        classes=["MyClass"],
        variables=["my_var"],
        case_sensitive=True,
    )

    # constant branch
    assert "A" in module_key("CONST", config_order, sub_imports=True)
    # classes branch
    assert "B" in module_key("MyClass", config_order, sub_imports=True)
    # variables branch
    assert "C" in module_key("my_var", config_order, sub_imports=True)
    # isupper() and len > 1 branch -> prefix 'A'
    assert "A" in module_key("SOME_UPPER", config_order, sub_imports=True)
    # module_name in config.classes or module_name[0:1].isupper() -> prefix 'B'
    assert "B" in module_key("Upperfirst", config_order, sub_imports=True)
    # else branch -> prefix 'C'
    assert "C" in module_key("lowerfirst", config_order, sub_imports=True)

    # 4. case_sensitive = False
    config_case_insensitive = Config(case_sensitive=False)
    res_ci = module_key("SomeModule", config_case_insensitive)
    assert res_ci.endswith("somemodule")

    # 5. length_sort branches:
    # config.length_sort
    config_ls1 = Config(length_sort=True, case_sensitive=True)
    assert ":" in module_key("abc", config_ls1)

    # config.length_sort_straight and straight_import
    config_ls2 = Config(length_sort_straight=True, case_sensitive=True)
    assert ":" in module_key("abc", config_ls2, straight_import=True)

    # str(section_name).lower() in config.length_sort_sections
    config_ls3 = Config(length_sort_sections=["thirdparty"], case_sensitive=True)
    assert ":" in module_key("abc", config_ls3, section_name="ThirdParty")

    # 6. force_to_top branch ('A' vs 'B')
    config_top = Config(force_to_top=["topmodule"], case_sensitive=True)
    res_top = module_key("topmodule", config_top)
    assert res_top.startswith("A")

    res_not_top = module_key("othermodule", config_top)
    assert res_not_top.startswith("B")
