# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

from isort.settings import Config
from isort.sorting import module_key

def test_module_key_full_coverage():
    # 1. Relative imports with reverse_relative = True and False
    config_rev = Config(reverse_relative=True)
    res_rev = module_key(".foo", config_rev)
    assert " " in res_rev

    config_normal_rel = Config(reverse_relative=False)
    res_norm_rel = module_key(".foo", config_normal_rel)
    assert "_" in res_norm_rel

    # 2. ignore_case = True vs False (when case_sensitive is True, ignore_case affects module_name transformation)
    config = Config(case_sensitive=True)
    key_ignore = module_key("Foo", config, ignore_case=True)
    key_no_ignore = module_key("Foo", config, ignore_case=False)
    assert key_ignore != key_no_ignore

    # 3. sub_imports and order_by_type branches:
    # constants, classes, variables, isupper len > 1, first char upper or in classes, else
    cfg_order = Config(
        order_by_type=True,
        constants={"CONST"},
        classes={"ClassA"},
        variables={"var"},
    )
    # constants -> prefix "A"
    assert "A" in module_key("CONST", cfg_order, sub_imports=True)
    # classes -> prefix "B"
    assert "B" in module_key("ClassA", cfg_order, sub_imports=True)
    # variables -> prefix "C"
    assert "C" in module_key("var", cfg_order, sub_imports=True)
    # isupper() and len > 1 -> prefix "A"
    assert "A" in module_key("ABC", cfg_order, sub_imports=True)
    # first char upper (or in classes) -> prefix "B"
    assert "B" in module_key("Somefunc", cfg_order, sub_imports=True)
    # else -> prefix "C"
    assert "C" in module_key("lowerfunc", cfg_order, sub_imports=True)

    # 4. case_sensitive = False
    cfg_insensitive = Config(case_sensitive=False)
    assert module_key("Foo", cfg_insensitive) == module_key("foo", cfg_insensitive)

    # 5. length_sort variations:
    # config.length_sort
    cfg_ls = Config(length_sort=True)
    assert ":" in module_key("foo", cfg_ls)

    # config.length_sort_straight and straight_import
    cfg_lss = Config(length_sort_straight=True)
    assert ":" in module_key("foo", cfg_lss, straight_import=True)

    # str(section_name).lower() in config.length_sort_sections
    cfg_lsec = Config(length_sort_sections={"custom"})
    assert ":" in module_key("foo", cfg_lsec, section_name="CUSTOM")

    # 6. force_to_top ('A' vs 'B' prefix at the very beginning)
    cfg_force = Config(force_to_top=["topmod"])
    key_top = module_key("topmod", cfg_force)
    key_normal = module_key("othermod", cfg_force)
    assert key_top.startswith("A")
    assert key_normal.startswith("B")
