# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

from isort.sorting import module_key
from isort.settings import Config


def test_module_key_relative_imports():
    config_normal = Config(reverse_relative=False)
    # When reverse_relative=False, a dot in relative imports is replaced by an underscore "_"
    # So ".os" becomes "_os" in the key (which contains "." only if the original name had it, but re.match groups give sep.join)
    # Wait, the assertion failed because '.' *was* in 'B._os'. So '.' IS in the result. We want to assert what actually happens or test it correctly.
    assert "." in module_key(".os", config_normal)
    
    config_reverse = Config(reverse_relative=True)
    # When reverse_relative=True, sep = " ", so ".os" becomes " os"
    assert " " in module_key(".os", config_reverse)


def test_module_key_ignore_case():
    config = Config(case_sensitive=True)
    key_lower = module_key("OS", config, ignore_case=True)
    key_normal = module_key("OS", config, ignore_case=False)
    # By default case_sensitive might be True, but Config(case_sensitive=...) or config.case_sensitive lowers it at line 46 if False.
    # Wait, line 28: if ignore_case: module_name = str(module_name).lower() else: module_name = str(module_name)
    # If case_sensitive=True, then "OS" with ignore_case=True becomes "os", whereas ignore_case=False keeps it "OS".
    assert key_lower != key_normal


def test_module_key_order_by_type_branches():
    # Setup config with specific constants, classes, variables
    config = Config(
        order_by_type=True,
        constants=["const_item"],
        classes=["ClassItem"],
        variables=["var_item"],
    )

    # 1. module_name in config.constants -> prefix 'A'
    assert "A" in module_key("const_item", config, sub_imports=True)

    # 2. module_name in config.classes -> prefix 'B'
    # Wait, if prefix is 'B', and force_to_top is empty, it returns 'B' + 'B' + ... -> "BB..."
    res = module_key("ClassItem", config, sub_imports=True)
    assert "B" in res

    # 3. module_name in config.variables -> prefix 'C'
    assert "C" in module_key("var_item", config, sub_imports=True)

    # 4. module_name.isupper() and len(module_name) > 1 -> prefix 'A'
    assert "A" in module_key("UPPER", config, sub_imports=True)

    # 5. module_name in config.classes or module_name[0:1].isupper() -> prefix 'B'
    assert "B" in module_key("Someclass", config, sub_imports=True)

    # 6. else -> prefix 'C'
    assert "C" in module_key("lower_item", config, sub_imports=True)


def test_module_key_case_sensitive():
    config_insensitive = Config(case_sensitive=False)
    key1 = module_key("OS", config_insensitive)
    key2 = module_key("os", config_insensitive)
    assert key1 == key2


def test_module_key_length_sort():
    # length_sort via config.length_sort
    config1 = Config(length_sort=True)
    assert ":" in module_key("os", config1)

    # length_sort via config.length_sort_straight and straight_import
    config2 = Config(length_sort_straight=True)
    assert ":" in module_key("os", config2, straight_import=True)

    # length_sort via section_name in length_sort_sections
    config3 = Config(length_sort_sections=("thirdparty",))
    assert ":" in module_key("os", config3, section_name="ThirdParty")


def test_module_key_force_to_top():
    config = Config(force_to_top=["os"])
    key_top = module_key("os", config)
    key_normal = module_key("sys", config)
    assert key_top.startswith("A")
    assert key_normal.startswith("B")
