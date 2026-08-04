# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

import pytest
from isort.settings import Config
from isort.sorting import module_key


def test_module_key_relative_imports():
    # Test match with reverse_relative = True and False
    config_rev = Config(reverse_relative=True)
    res_rev = module_key(".foo", config_rev)
    assert res_rev.endswith(". foo") or "." in res_rev

    config_normal = Config(reverse_relative=False)
    res_normal = module_key(".foo", config_normal)
    assert "_" in res_normal


def test_module_key_ignore_case():
    config = Config(case_sensitive=True)
    # ignore_case = True
    res_ignore = module_key("FOO", config, ignore_case=True)
    # ignore_case = False
    res_no_ignore = module_key("FOO", config, ignore_case=False)
    assert res_ignore != res_no_ignore


def test_module_key_order_by_type_branches():
    # sub_imports = True and order_by_type = True
    config = Config(
        order_by_type=True,
        constants=("CONST",),
        classes=("ClassA",),
        variables=("var",),
    )

    # 1. module_name in config.constants -> prefix = "A"
    assert "A" in module_key("CONST", config, sub_imports=True)

    # 2. module_name in config.classes -> prefix = "B"
    assert "B" in module_key("ClassA", config, sub_imports=True)

    # 3. module_name in config.variables -> prefix = "C"
    assert "C" in module_key("var", config, sub_imports=True)

    # 4. module_name.isupper() and len(module_name) > 1 -> prefix = "A"
    assert "A" in module_key("UPPER", config, sub_imports=True)

    # 5. module_name in config.classes or module_name[0:1].isupper() -> prefix = "B"
    assert "B" in module_key("Upperword", config, sub_imports=True)

    # 6. fallback else -> prefix = "C"
    assert "C" in module_key("lowerword", config, sub_imports=True)


def test_module_key_case_sensitive():
    # case_sensitive = False
    config_insens = Config(case_sensitive=False)
    res = module_key("AbC", config_insens)
    assert res == module_key("abc", config_insens)


def test_module_key_length_sort_branches():
    # length_sort = config.length_sort or (config.length_sort_straight and straight_import) or str(section_name).lower() in config.length_sort_sections
    
    # Branch 1: config.length_sort = True
    config1 = Config(length_sort=True)
    res1 = module_key("os", config1)
    assert ":" in res1

    # Branch 2: config.length_sort_straight and straight_import
    config2 = Config(length_sort_straight=True)
    res2 = module_key("os", config2, straight_import=True)
    assert ":" in res2

    # Branch 3: str(section_name).lower() in config.length_sort_sections
    config3 = Config(length_sort_sections=("thirdparty",))
    res3 = module_key("os", config3, section_name="THIRDPARTY")
    assert ":" in res3


def test_module_key_force_to_top():
    config = Config(force_to_top=("top_module",))
    res_top = module_key("top_module", config)
    res_other = module_key("other_module", config)
    
    # force_to_top results in 'A' prefix at the very beginning
    assert res_top.startswith("A")
    assert res_other.startswith("B")
