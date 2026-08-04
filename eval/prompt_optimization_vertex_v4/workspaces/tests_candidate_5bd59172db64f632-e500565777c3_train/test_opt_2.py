# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

import pytest
from isort.settings import Config
from isort.sorting import module_key


def test_module_key_relative_and_case():
    # 1. relative import with reverse_relative = True
    config = Config(reverse_relative=True, case_sensitive=True)
    res = module_key(".os", config=config, ignore_case=False)
    assert "." in res or "_" in res or " " in res

    # 2. ignore_case = True vs False
    config2 = Config(case_sensitive=True)
    key_ignore = module_key("OS", config=config2, ignore_case=True)
    key_no_ignore = module_key("OS", config=config2, ignore_case=False)
    assert key_ignore != key_no_ignore


def test_module_key_order_by_type_branches():
    # constants, classes, variables, isupper & len>1, classes/isupper, else
    config = Config(
        order_by_type=True,
        constants=["const_item"],
        classes=["class_item", "UpperClass"],
        variables=["var_item"],
    )

    # constants -> prefix 'A'
    assert "A" in module_key("const_item", config, sub_imports=True)

    # classes -> prefix 'B'
    assert "B" in module_key("class_item", config, sub_imports=True)

    # variables -> prefix 'C'
    assert "C" in module_key("var_item", config, sub_imports=True)

    # isupper and len > 1 -> prefix 'A'
    assert "A" in module_key("UPPER", config, sub_imports=True)

    # module_name in config.classes or module_name[0:1].isupper() -> prefix 'B'
    assert "B" in module_key("UpperClass", config, sub_imports=True)
    assert "B" in module_key("Someothercapitalized", config, sub_imports=True)

    # else -> prefix 'C'
    assert "C" in module_key("lowercase_other", config, sub_imports=True)


def test_module_key_case_sensitive_and_length_sort():
    # case_sensitive = False -> lowercases module_name
    config_case = Config(case_sensitive=False)
    res = module_key("MyModule", config_case)
    assert "mymodule" in res

    # length_sort options:
    # 1. config.length_sort = True
    config_len1 = Config(length_sort=True)
    assert ":" in module_key("foo", config_len1)

    # 2. config.length_sort_straight and straight_import
    config_len2 = Config(length_sort_straight=True)
    assert ":" in module_key("foo", config_len2, straight_import=True)

    # 3. str(section_name).lower() in config.length_sort_sections
    config_len3 = Config(length_sort_sections=("custom_section",))
    assert ":" in module_key("foo", config_len3, section_name="CUSTOM_SECTION")


def test_module_key_force_to_top():
    config = Config(force_to_top=("top_module",))
    # force_to_top -> 'A', else 'B'
    key_top = module_key("top_module", config)
    key_other = module_key("other_module", config)

    assert key_top.startswith("A")
    assert key_other.startswith("B")
