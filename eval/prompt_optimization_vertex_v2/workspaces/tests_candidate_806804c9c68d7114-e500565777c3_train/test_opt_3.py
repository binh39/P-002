# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47]]}

import pytest
from isort.sorting import module_key
from isort.settings import Config


def test_module_key_full_coverage():
    # Test relative module name with reverse_relative=True and False
    config_rev = Config(reverse_relative=True)
    res_rev = module_key(".os", config=config_rev)
    assert res_rev is not None

    config_normal = Config(reverse_relative=False)
    res_normal = module_key(".os", config=config_normal)
    assert res_normal is not None

    # Test ignore_case = True vs False
    config = Config()
    res_ignore = module_key("OS", config=config, ignore_case=True)
    assert res_ignore is not None
    res_no_ignore = module_key("OS", config=config, ignore_case=False)
    assert res_no_ignore is not None

    # Test sub_imports and order_by_type branches:
    # 1. module_name in config.constants (prefix 'A')
    # 2. module_name in config.classes (prefix 'B')
    # 3. module_name in config.variables (prefix 'C')
    # 4. module_name.isupper() and len(module_name) > 1 (prefix 'A')
    # 5. module_name[0:1].isupper() (prefix 'B')
    # 6. else (prefix 'C')
    config_order = Config(
        order_by_type=True,
        constants=["CONST"],
        classes=["MyClass"],
        variables=["my_var"],
    )

    assert "A" in module_key("CONST", config=config_order, sub_imports=True)
    assert "B" in module_key("MyClass", config=config_order, sub_imports=True)
    assert "C" in module_key("my_var", config=config_order, sub_imports=True)
    assert "A" in module_key("UPPER", config=config_order, sub_imports=True)
    assert "B" in module_key("Upperfirst", config=config_order, sub_imports=True)
    assert "C" in module_key("lowerfirst", config=config_order, sub_imports=True)

    # Test case_sensitive = False
    config_case = Config(case_sensitive=False)
    assert module_key("OS", config=config_case) is not None

    # Test length_sort combinations:
    # - config.length_sort = True
    # - config.length_sort_straight = True and straight_import = True
    # - str(section_name).lower() in config.length_sort_sections
    config_ls1 = Config(length_sort=True)
    assert module_key("os", config=config_ls1) is not None

    config_ls2 = Config(length_sort_straight=True)
    assert module_key("os", config=config_ls2, straight_import=True) is not None

    config_ls3 = Config(length_sort_sections=["thirdparty"])
    assert module_key("os", config=config_ls3, section_name="ThirdParty") is not None

    # Test force_to_top ('A' vs 'B')
    config_top = Config(force_to_top=["os"])
    res_top = module_key("os", config=config_top)
    assert res_top.startswith("A")

    res_not_top = module_key("sys", config=config_top)
    assert res_not_top.startswith("B")
