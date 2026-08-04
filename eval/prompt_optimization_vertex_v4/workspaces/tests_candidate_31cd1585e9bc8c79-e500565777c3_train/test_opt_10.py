# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

import pytest
from isort.settings import Config
from isort.sorting import module_key


def test_module_key_relative_imports():
    config_normal = Config(reverse_relative=False)
    assert module_key(".os", config_normal) == "B._os"

    config_reverse = Config(reverse_relative=True)
    assert module_key(".os", config_reverse) == "B. os"


def test_module_key_ignore_case():
    config = Config(case_sensitive=True)
    assert module_key("OS", config, ignore_case=True) == "Bos"
    assert module_key("OS", config, ignore_case=False) == "BOS"


def test_module_key_order_by_type_branches():
    # Test sub_imports and order_by_type paths
    # 1. module_name in config.constants -> prefix 'A'
    config = Config(
        order_by_type=True,
        constants=["my_const"],
        classes=["MyClass"],
        variables=["my_var"],
        case_sensitive=True,
    )
    assert module_key("my_const", config, sub_imports=True) == "BAmy_const"

    # 2. module_name in config.classes -> prefix 'B'
    assert module_key("MyClass", config, sub_imports=True, ignore_case=False) == "BBMyClass"

    # 3. module_name in config.variables -> prefix 'C'
    assert module_key("my_var", config, sub_imports=True) == "BCmy_var"

    # 4. module_name.isupper() and len(module_name) > 1 -> prefix 'A'
    assert "BA" in module_key("CONST", config, sub_imports=True)

    # 5. module_name[0:1].isupper() -> prefix 'B'
    assert "BB" in module_key("OtherClass", config, sub_imports=True, ignore_case=False)

    # 6. fallback else -> prefix 'C'
    assert module_key("lowercase_func", config, sub_imports=True) == "BClowercase_func"


def test_module_key_case_sensitive():
    config_insensitive = Config(case_sensitive=False)
    assert module_key("OS", config_insensitive) == "Bos"

    config_sensitive = Config(case_sensitive=True)
    assert module_key("OS", config_sensitive) == "BOS"


def test_module_key_length_sort():
    # length_sort = config.length_sort or (config.length_sort_straight and straight_import) or str(section_name).lower() in config.length_sort_sections
    
    # Path 1: config.length_sort
    config1 = Config(length_sort=True)
    res1 = module_key("os", config1)
    assert res1.startswith("B2:")

    # Path 2: config.length_sort_straight and straight_import
    config2 = Config(length_sort_straight=True)
    res2 = module_key("os", config2, straight_import=True)
    assert res2.startswith("B2:")

    # Path 3: str(section_name).lower() in config.length_sort_sections
    config3 = Config(length_sort_sections=["thirdparty"])
    res3 = module_key("os", config3, section_name="ThirdParty")
    assert res3.startswith("B2:")

    # No length sort
    config4 = Config(case_sensitive=True)
    res4 = module_key("OS", config4)
    assert res4 == "BOS"


def test_module_key_force_to_top():
    config = Config(force_to_top=["os"])
    res = module_key("os", config)
    assert res.startswith("A")

    res_normal = module_key("sys", config)
    assert res_normal.startswith("B")
