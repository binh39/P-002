# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47]]}

from isort.settings import Config
from isort.sorting import module_key


def test_module_key_comprehensive():
    # Test relative module with reverse_relative = True and False
    config_rev = Config(reverse_relative=True)
    res1 = module_key(".os", config=config_rev)
    assert res1.startswith("B")

    config_norm = Config(reverse_relative=False)
    res2 = module_key(".os", config=config_norm)
    assert res2.startswith("B")

    # Test case_sensitive = False
    config_cs = Config(case_sensitive=False, constants=["CONST"])
    assert module_key("CONST", config=config_cs) is not None

    # Test sub_imports and order_by_type branches:
    # 1. module_name in config.constants -> prefix 'A'
    # 2. module_name in config.classes -> prefix 'B'
    # 3. module_name in config.variables -> prefix 'C'
    # 4. module_name.isupper() and len(module_name) > 1 -> prefix 'A'
    # 5. module_name in config.classes or module_name[0:1].isupper() -> prefix 'B'
    # 6. else -> prefix 'C'
    config_order = Config(
        order_by_type=True,
        constants=["my_const"],
        classes=["MyClass"],
        variables=["my_var"],
    )

    # constants
    assert "A" in module_key("my_const", config=config_order, sub_imports=True)
    # classes
    assert "B" in module_key("MyClass", config=config_order, sub_imports=True)
    # variables
    assert "C" in module_key("my_var", config=config_order, sub_imports=True)
    # isupper and len > 1
    assert "A" in module_key("UPPER", config=config_order, sub_imports=True)
    # module_name[0:1].isupper() but not in classes/constants/variables/isupper
    assert "B" in module_key("Other", config=config_order, sub_imports=True)
    # else branch (lowercase, not in constants/classes/variables)
    assert "C" in module_key("lower", config=config_order, sub_imports=True)

    # Test force_to_top ('A' vs 'B' branch)
    config_top = Config(force_to_top=["top_mod"])
    assert module_key("top_mod", config=config_top).startswith("A")
    assert module_key("other_mod", config=config_top).startswith("B")

    # Test length_sort combinations:
    # length_sort = config.length_sort or (config.length_sort_straight and straight_import) or str(section_name).lower() in config.length_sort_sections
    config_ls1 = Config(length_sort=True)
    assert ":" in module_key("foo", config=config_ls1)

    config_ls2 = Config(length_sort_straight=True)
    assert ":" in module_key("foo", config=config_ls2, straight_import=True)

    config_ls3 = Config(length_sort_sections=["sec"])
    assert ":" in module_key("foo", config=config_ls3, section_name="SEC")
