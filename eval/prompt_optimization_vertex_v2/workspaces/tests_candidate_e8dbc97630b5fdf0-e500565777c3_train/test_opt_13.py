# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

import pytest
from isort.settings import Config
from isort.sorting import module_key


def test_module_key_relative_imports():
    config_normal = Config(reverse_relative=False)
    key_normal = module_key(".os", config_normal)
    assert "_" in key_normal

    config_reverse = Config(reverse_relative=True)
    key_reverse = module_key(".os", config_reverse)
    assert " " in key_reverse


def test_module_key_ignore_case():
    config = Config(case_sensitive=True)
    key_ignore = module_key("OS", config, ignore_case=True)
    key_no_ignore = module_key("OS", config, ignore_case=False)
    assert key_ignore == "Bos"
    assert key_no_ignore == "BOS"


def test_module_key_order_by_type_branches():
    # Setup config with specific constants, classes, variables
    config = Config(
        order_by_type=True,
        constants=["const_val"],
        classes=["ClassVal"],
        variables=["var_val"],
    )

    # 1. module_name in config.constants -> prefix 'A'
    assert "A" in module_key("const_val", config, sub_imports=True)

    # 2. module_name in config.classes -> prefix 'B'
    assert "B" in module_key("ClassVal", config, sub_imports=True)

    # 3. module_name in config.variables -> prefix 'C'
    assert "C" in module_key("var_val", config, sub_imports=True)

    # 4. module_name.isupper() and len(module_name) > 1 -> prefix 'A'
    assert "A" in module_key("UPPER", config, sub_imports=True)

    # 5. module_name in config.classes or module_name[0:1].isupper() -> prefix 'B'
    assert "B" in module_key("Upperone", config, sub_imports=True)

    # 6. else -> prefix 'C'
    assert "C" in module_key("lowerone", config, sub_imports=True)


def test_module_key_case_sensitive():
    config_insensitive = Config(case_sensitive=False)
    key1 = module_key("Os", config_insensitive)
    
    config_sensitive = Config(case_sensitive=True)
    key2 = module_key("Os", config_sensitive)
    
    assert key1 != key2




def test_module_key_force_to_top():
    config = Config(force_to_top=["os"])
    key_top = module_key("os", config)
    key_normal = module_key("sys", config)
    
    assert key_top.startswith("A")
    assert key_normal.startswith("B")
