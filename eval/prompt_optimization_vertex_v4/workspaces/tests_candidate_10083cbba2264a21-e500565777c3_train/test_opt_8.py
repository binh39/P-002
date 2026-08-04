# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

from isort.sorting import module_key
from isort.settings import Config


def test_module_key_comprehensive():
    # Test 1: match relative import with reverse_relative = True
    config_rev = Config(reverse_relative=True, case_sensitive=True)
    res1 = module_key(".os", config=config_rev)
    assert res1.endswith("os")

    # Test 2: match relative import with reverse_relative = False (default)
    config_norm = Config(reverse_relative=False, case_sensitive=True)
    res2 = module_key(".os", config=config_norm)
    assert res2.endswith("os")

    # Test 3: ignore_case and force_to_top, case_sensitive = False
    config_ic = Config(
        case_sensitive=False,
        force_to_top=["os"],
    )
    res3 = module_key("OS", config=config_ic, ignore_case=True)
    assert res3.startswith("A")

    config_ic_false = Config(
        case_sensitive=True,
        force_to_top=[],
    )
    res3_b = module_key("os", config=config_ic_false, ignore_case=False)
    assert res3_b.startswith("B")

    # Test 4: sub_imports and order_by_type branches:
    # constants, classes, variables, isupper and len > 1, classes/isupper, else (C)
    config_obt = Config(
        order_by_type=True,
        constants=["const"],
        classes=["myclass"],
        variables=["myvar"],
        case_sensitive=True,
    )

    # constant (prefix A)
    assert module_key("const", config=config_obt, sub_imports=True).startswith("BA")
    # class (prefix B)
    assert module_key("myclass", config=config_obt, sub_imports=True).startswith("BB")
    # variable (prefix C)
    assert module_key("myvar", config=config_obt, sub_imports=True).startswith("BC")
    # isupper and len > 1 (prefix A)
    assert module_key("ABC", config=config_obt, sub_imports=True).startswith("BA")
    # first char isupper (prefix B)
    assert module_key("Someclass", config=config_obt, sub_imports=True).startswith("BB")
    # fallback else (prefix C)
    assert module_key("lowerz", config=config_obt, sub_imports=True).startswith("BC")

    # Test 5: length_sort options
    # config.length_sort = True
    cfg_ls1 = Config(length_sort=True, case_sensitive=True)
    assert ":" in module_key("abc", config=cfg_ls1)

    # config.length_sort_straight and straight_import = True
    cfg_ls2 = Config(length_sort_straight=True, case_sensitive=True)
    assert ":" in module_key("abc", config=cfg_ls2, straight_import=True)

    # str(section_name).lower() in config.length_sort_sections
    cfg_ls3 = Config(length_sort_sections=["thirdparty"], case_sensitive=True)
    assert ":" in module_key("abc", config=cfg_ls3, section_name="ThirdParty")
