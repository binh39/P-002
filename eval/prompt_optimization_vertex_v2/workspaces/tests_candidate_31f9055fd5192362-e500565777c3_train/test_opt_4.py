# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47]]}

from isort.sorting import module_key
from isort.settings import Config


def test_module_key_relative_imports():
    # Test line 22-25: match with relative import
    config1 = Config(reverse_relative=False)
    assert module_key(".os", config1) == "B._os"

    config2 = Config(reverse_relative=True)
    assert module_key("..sys", config2) == "B.. sys"


def test_module_key_ignore_case():
    # Test line 28-31: ignore_case True vs False
    config = Config()
    assert module_key("OS", config, ignore_case=True) == "Bos"
    assert module_key("OS", config, ignore_case=False) == "Bos"


def test_module_key_order_by_type_branches():
    # Test sub_imports and config.order_by_type branches (lines 33-45)
    # Constants, classes, variables, isupper len>1, first letter upper, else (C)
    config = Config(
        order_by_type=True,
        constants=["const_item"],
        classes=["ClassItem"],
        variables=["var_item"],
    )

    # 1. module_name in config.constants -> prefix 'A'
    assert module_key("const_item", config, sub_imports=True) == "BAconst_item"

    # 2. module_name in config.classes -> prefix 'B'
    assert module_key("ClassItem", config, sub_imports=True) == "BBclassitem"

    # 3. module_name in config.variables -> prefix 'C'
    assert module_key("var_item", config, sub_imports=True) == "BCvar_item"

    # 4. module_name.isupper() and len(module_name) > 1 -> prefix 'A'
    assert module_key("ABC", config, sub_imports=True) == "BAabc"

    # 5. module_name[0:1].isupper() (or in config.classes) -> prefix 'B'
    assert module_key("Someother", config, sub_imports=True) == "BBsomeother"

    # 6. else -> prefix 'C'
    assert module_key("lower_item", config, sub_imports=True) == "BClower_item"


def test_module_key_case_sensitive():
    # Test line 46-47: not config.case_sensitive
    config = Config(case_sensitive=False)
    assert module_key("OS", config) == "Bos"


def test_module_key_length_sort():
    # Test lines 49-52: length_sort combinations
    # length_sort, length_sort_straight & straight_import, length_sort_sections & section_name
    
    # length_sort = True
    config_ls = Config(length_sort=True)
    assert module_key("os", config_ls) == "B2:os"

    # length_sort_straight=True, straight_import=True
    config_lss = Config(length_sort_straight=True)
    assert module_key("os", config_lss, straight_import=True) == "B2:os"
    assert module_key("os", config_lss, straight_import=False) == "Bos"

    # length_sort_sections containing section_name
    config_lsec = Config(length_sort_sections=["thirdparty"])
    assert module_key("os", config_lsec, section_name="ThirdParty") == "B2:os"
    assert module_key("os", config_lsec, section_name="Standard") == "Bos"


def test_module_key_force_to_top():
    # Test line 55: module_name in config.force_to_top -> 'A', else 'B'
    config = Config(force_to_top=["os"])
    assert module_key("os", config) == "Aos"
    assert module_key("sys", config) == "Bsys"
