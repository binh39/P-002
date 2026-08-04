# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

import pytest
from isort.sorting import module_key
from isort.settings import Config


def test_module_key_comprehensive():
    # Test relative module with reverse_relative True
    config_rev = Config(reverse_relative=True, case_sensitive=True)
    res_rev = module_key(".os", config=config_rev)
    assert res_rev.endswith("os")

    # Test relative module with reverse_relative False
    config_no_rev = Config(reverse_relative=False, case_sensitive=True)
    res_no_rev = module_key(".os", config=config_no_rev)
    assert res_no_rev.endswith("os")

    # Test ignore_case=True
    config_ic = Config(case_sensitive=True)
    res_ic = module_key("OS", config=config_ic, ignore_case=True)
    assert "os" in res_ic

    # Test sub_imports and order_by_type branches
    # 1. module in constants -> prefix 'A'
    cfg_obt1 = Config(order_by_type=True, constants=("CONST",), case_sensitive=True)
    assert "A" in module_key("CONST", config=cfg_obt1, sub_imports=True)

    # 2. module in classes -> prefix 'B'
    cfg_obt2 = Config(order_by_type=True, classes=("MyClass",), case_sensitive=True)
    assert "B" in module_key("MyClass", config=cfg_obt2, sub_imports=True)

    # 3. module in variables -> prefix 'C'
    cfg_obt3 = Config(order_by_type=True, variables=("my_var",), case_sensitive=True)
    assert "C" in module_key("my_var", config=cfg_obt3, sub_imports=True)

    # 4. module.isupper() and len > 1 -> prefix 'A'
    cfg_obt4 = Config(order_by_type=True, case_sensitive=True)
    assert "A" in module_key("ABC", config=cfg_obt4, sub_imports=True)

    # 5. module in classes or starts with upper -> prefix 'B'
    cfg_obt5 = Config(order_by_type=True, case_sensitive=True)
    assert "B" in module_key("Foo", config=cfg_obt5, sub_imports=True)

    # 6. fallback else -> prefix 'C'
    cfg_obt6 = Config(order_by_type=True, case_sensitive=True)
    assert "C" in module_key("foo", config=cfg_obt6, sub_imports=True)

    # Test not config.case_sensitive
    cfg_insensitive = Config(case_sensitive=False)
    res_insens = module_key("FooBar", config=cfg_insensitive)
    assert "foobar" in res_insens

    # Test length_sort variations
    # length_sort = True
    cfg_ls1 = Config(length_sort=True, case_sensitive=True)
    assert ":" in module_key("os", config=cfg_ls1)

    # length_sort_straight and straight_import = True
    cfg_lss = Config(length_sort_straight=True, case_sensitive=True)
    assert ":" in module_key("os", config=cfg_lss, straight_import=True)

    # section_name in length_sort_sections
    cfg_lss_sec = Config(length_sort_sections=("thirdparty",), case_sensitive=True)
    assert ":" in module_key("os", config=cfg_lss_sec, section_name="ThirdParty")

    # Test force_to_top
    cfg_top = Config(force_to_top=("os",), case_sensitive=True)
    res_top = module_key("os", config=cfg_top)
    assert res_top.startswith("A")

    cfg_not_top = Config(force_to_top=(), case_sensitive=True)
    res_not_top = module_key("os", config=cfg_not_top)
    assert res_not_top.startswith("B")
