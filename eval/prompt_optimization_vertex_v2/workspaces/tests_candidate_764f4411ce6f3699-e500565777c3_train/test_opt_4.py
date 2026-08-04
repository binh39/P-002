# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47]]}

from isort.settings import Config
from isort.sorting import module_key


def test_module_key_comprehensive():
    # Test relative import with reverse_relative = True
    config_rev = Config(reverse_relative=True)
    res_rev = module_key(".os", config_rev)
    assert ". os" in res_rev

    # Test ignore_case = True
    config_basic = Config()
    res_ignore = module_key("OS", config_basic, ignore_case=True)
    assert "os" in res_ignore

    # Test sub_imports and order_by_type with constants, classes, variables, isuppers, etc.
    config_order = Config(
        order_by_type=True,
        constants=["const"],
        classes=["myclass"],
        variables=["var"],
    )

    # 1. module_name in config.constants -> prefix 'A'
    assert "A" in module_key("const", config_order, sub_imports=True)

    # 2. module_name in config.classes -> prefix 'B'
    assert "B" in module_key("myclass", config_order, sub_imports=True)

    # 3. module_name in config.variables -> prefix 'C'
    assert "C" in module_key("var", config_order, sub_imports=True)

    # 4. module_name.isupper() and len > 1 -> prefix 'A'
    assert "A" in module_key("CONST", config_order, sub_imports=True)

    # 5. module_name in config.classes or module_name[0:1].isupper() -> prefix 'B'
    assert "B" in module_key("UpperName", config_order, sub_imports=True)

    # 6. else -> prefix 'C'
    assert "C" in module_key("lowercase", config_order, sub_imports=True)

    # Test case_sensitive = False
    config_case = Config(case_sensitive=False)
    res_case = module_key("Os", config_case)
    assert "os" in res_case

    # Test length_sort permutations:
    # length_sort_straight and straight_import
    config_len1 = Config(length_sort_straight=True)
    res_len1 = module_key("os", config_len1, straight_import=True)
    assert ":" in res_len1

    # str(section_name).lower() in config.length_sort_sections
    config_len2 = Config(length_sort_sections=["thirdparty"])
    res_len2 = module_key("os", config_len2, section_name="ThirdParty")
    assert ":" in res_len2

    # Test force_to_top -> 'A' vs 'B' prefix at the very beginning
    config_top = Config(force_to_top=["os"])
    res_top = module_key("os", config_top)
    assert res_top.startswith("A")

    res_not_top = module_key("sys", config_top)
    assert res_not_top.startswith("B")
