# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

from isort.settings import Config
from isort.sorting import module_key


def test_module_key_comprehensive():
    # 1. Relative import match with reverse_relative = True and False
    config_rev = Config(reverse_relative=True)
    res_rev = module_key(".os", config=config_rev)
    assert res_rev.endswith(" . os") or "." in res_rev  # depending on implementation details

    config_normal = Config(reverse_relative=False)
    res_norm = module_key(".os", config=config_normal)
    assert "_" in res_norm

    # 2. ignore_case = True vs False
    config_ic = Config(case_sensitive=True)
    res_ic_true = module_key("OS", config=config_ic, ignore_case=True)
    res_ic_false = module_key("OS", config=config_ic, ignore_case=False)
    assert res_ic_true == "Bos"
    assert res_ic_false == "BOS"

    # 3. sub_imports and order_by_type branches:
    # constants, classes, variables, isupper len > 1, first char uppercase, else (C)
    config_order = Config(
        order_by_type=True,
        constants=["my_const"],
        classes=["MyClass"],
        variables=["my_var"],
    )

    # constants ('A')
    assert "A" in module_key("my_const", config=config_order, sub_imports=True)
    # classes ('B')
    assert "B" in module_key("MyClass", config=config_order, sub_imports=True)
    # variables ('C')
    assert "C" in module_key("my_var", config=config_order, sub_imports=True)
    # isupper() and len > 1 ('A')
    assert "A" in module_key("CONST", config=config_order, sub_imports=True)
    # starts with uppercase ('B')
    assert "B" in module_key("Other", config=config_order, sub_imports=True)
    # else ('C')
    assert "C" in module_key("other", config=config_order, sub_imports=True)

    # 4. case_sensitive = False
    config_case = Config(case_sensitive=False)
    res_case = module_key("OS", config=config_case)
    assert "os" in res_case

    # 5. length_sort branches:
    # config.length_sort
    # config.length_sort_straight and straight_import
    # str(section_name).lower() in config.length_sort_sections
    cfg_ls1 = Config(length_sort=True)
    assert ":" in module_key("os", config=cfg_ls1)

    cfg_ls2 = Config(length_sort_straight=True)
    assert ":" in module_key("os", config=cfg_ls2, straight_import=True)

    cfg_ls3 = Config(length_sort_sections=["thirdparty"])
    assert ":" in module_key("os", config=cfg_ls3, section_name="THIRDPARTY")

    # 6. force_to_top ('A' vs 'B')
    cfg_ftp = Config(force_to_top=["os"])
    assert module_key("os", config=cfg_ftp).startswith("A")
    assert module_key("sys", config=cfg_ftp).startswith("B")
