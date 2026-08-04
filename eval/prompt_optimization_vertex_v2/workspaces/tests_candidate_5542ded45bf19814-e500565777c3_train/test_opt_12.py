# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47]]}

from isort.sorting import module_key
from isort.settings import Config


def test_module_key_relative_imports():
    config_normal = Config(reverse_relative=False)
    config_reverse = Config(reverse_relative=True)

    # Line 22-25: match with relative import dots
    key1 = module_key(".os", config_normal)
    assert key1.endswith("._os")

    key2 = module_key(".os", config_reverse)
    assert key2.endswith(". os")




def test_module_key_order_by_type_branches():
    # Test sub_imports and order_by_type paths (lines 33-45)
    config = Config(
        order_by_type=True,
        constants=["CONST"],
        classes=["MyClass"],
        variables=["var"],
    )

    # Line 34-35: module_name in config.constants -> 'A'
    assert "A" in module_key("CONST", config, sub_imports=True)

    # Line 36-37: module_name in config.classes -> 'B'
    assert "B" in module_key("MyClass", config, sub_imports=True)

    # Line 38-39: module_name in config.variables -> 'C'
    assert "C" in module_key("var", config, sub_imports=True)

    # Line 40-41: isupper() and len > 1 -> 'A'
    assert "A" in module_key("UPPER", config, sub_imports=True)

    # Line 42-43: module_name[0:1].isupper() -> 'B'
    assert "B" in module_key("SomeOther", config, sub_imports=True)

    # Line 44-45: else -> 'C'
    assert "C" in module_key("lower", config, sub_imports=True)


def test_module_key_case_sensitive():
    # Line 46-47: not config.case_sensitive
    config_insensitive = Config(case_sensitive=False)
    key = module_key("AbC", config_insensitive)
    assert "abc" in key


def test_module_key_length_sort_branches():
    # Test length_sort combinations (lines 49-54)
    # 1. config.length_sort = True
    config1 = Config(length_sort=True)
    assert ":" in module_key("os", config1)

    # 2. config.length_sort_straight and straight_import
    config2 = Config(length_sort_straight=True)
    assert ":" in module_key("os", config2, straight_import=True)

    # 3. str(section_name).lower() in config.length_sort_sections
    config3 = Config(length_sort_sections=["thirdparty"])
    assert ":" in module_key("os", config3, section_name="ThirdParty")


def test_module_key_force_to_top():
    # Line 55: force_to_top condition ('A' vs 'B')
    config = Config(force_to_top=["os"])
    key_top = module_key("os", config)
    key_normal = module_key("sys", config)

    assert key_top.startswith("A")
    assert key_normal.startswith("B")
