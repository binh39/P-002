# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

from isort.sorting import module_key
from isort.settings import Config


def test_module_key_comprehensive():
    # Test line 22-25: match with reverse_relative True and False
    config_rev = Config(reverse_relative=True)
    res1 = module_key(".foo", config_rev)
    assert "_" not in res1  # Uses space for reverse_relative=True

    config_norm = Config(reverse_relative=False)
    res2 = module_key(".foo", config_norm)
    assert "_" in res2  # Uses underscore when reverse_relative=False

    # Test line 28-31: ignore_case True and False
    # Note: by default case_sensitive might be False, making case differences get lowercased anyway unless case_sensitive=True.
    config = Config(case_sensitive=True)
    key_ignore = module_key("Foo", config, ignore_case=True)
    key_no_ignore = module_key("Foo", config, ignore_case=False)
    assert key_ignore != key_no_ignore

    # Test lines 33-45: sub_imports and order_by_type branches
    # config.constants, config.classes, config.variables
    cfg_order = Config(
        order_by_type=True,
        constants=["CONST"],
        classes=["MyClass"],
        variables=["my_var"],
    )

    # 1. module_name in config.constants -> prefix 'A'
    assert "A" in module_key("CONST", cfg_order, sub_imports=True)

    # 2. module_name in config.classes -> prefix 'B'
    assert "B" in module_key("MyClass", cfg_order, sub_imports=True)

    # 3. module_name in config.variables -> prefix 'C'
    assert "C" in module_key("my_var", cfg_order, sub_imports=True)

    # 4. module_name.isupper() and len(module_name) > 1 -> prefix 'A'
    assert "A" in module_key("UPPER", cfg_order, sub_imports=True)

    # 5. module_name[0:1].isupper() -> prefix 'B'
    assert "B" in module_key("Uppercase", cfg_order, sub_imports=True)

    # 6. fallback else -> prefix 'C'
    assert "C" in module_key("lowercase", cfg_order, sub_imports=True)

    # Test line 46-47: not config.case_sensitive
    cfg_case_insensitive = Config(case_sensitive=False)
    key_ci = module_key("Foo", cfg_case_insensitive)
    assert "foo" in key_ci

    # Test lines 49-52: length_sort evaluation (length_sort, length_sort_straight + straight_import, length_sort_sections + section_name)
    cfg_ls = Config(length_sort=True)
    assert ":" in module_key("foo", cfg_ls)

    cfg_lss = Config(length_sort_straight=True)
    assert ":" in module_key("foo", cfg_lss, straight_import=True)

    cfg_lss_sec = Config(length_sort_sections=["thirdparty"])
    assert ":" in module_key("foo", cfg_lss_sec, section_name="ThirdParty")

    # Test line 55: force_to_top ('A' vs 'B')
    cfg_top = Config(force_to_top=["foo"])
    key_top = module_key("foo", cfg_top)
    key_not_top = module_key("bar", cfg_top)
    assert key_top.startswith("A")
    assert key_not_top.startswith("B")
