# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

from isort.sorting import module_key
from isort.settings import Config


def test_module_key_relative_imports():
    config_rev = Config(reverse_relative=True)
    res_rev = module_key(".os", config=config_rev)
    assert "." in res_rev or " " in res_rev

    config_normal = Config(reverse_relative=False)
    res_normal = module_key(".os", config=config_normal)
    assert "_" in res_normal


def test_module_key_ignore_case():
    config = Config()
    res_ignore = module_key("OS", config=config, ignore_case=True)
    res_keep = module_key("OS", config=config, ignore_case=False)
    assert res_ignore.endswith("os")
    # By default, Config.case_sensitive is False, so module_name gets lowercased at line 46-47 anyway.
    # To test ignore_case=False keeping casing, case_sensitive must be True.
    config_sensitive = Config(case_sensitive=True)
    res_keep_sens = module_key("OS", config=config_sensitive, ignore_case=False)
    assert res_keep_sens.endswith("OS")


def test_module_key_order_by_type_branches():
    config = Config(
        order_by_type=True,
        constants=("MY_CONST",),
        classes=("MyClass",),
        variables=("my_var",),
    )
    
    # 1. module_name in config.constants -> prefix 'A'
    assert "A" in module_key("MY_CONST", config=config, sub_imports=True)
    
    # 2. module_name in config.classes -> prefix 'B'
    assert "B" in module_key("MyClass", config=config, sub_imports=True)
    
    # 3. module_name in config.variables -> prefix 'C'
    assert "C" in module_key("my_var", config=config, sub_imports=True)
    
    # 4. module_name.isupper() and len(module_name) > 1 -> prefix 'A'
    assert "A" in module_key("OTHER_CONST", config=config, sub_imports=True)
    
    # 5. module_name[0:1].isupper() -> prefix 'B'
    assert "B" in module_key("OtherClass", config=config, sub_imports=True)
    
    # 6. else -> prefix 'C'
    assert "C" in module_key("lower_func", config=config, sub_imports=True)


def test_module_key_case_sensitive():
    config_insensitive = Config(case_sensitive=False)
    res = module_key("OS", config=config_insensitive)
    assert res.endswith("os")


def test_module_key_length_sort():
    config1 = Config(length_sort=True)
    assert ":" in module_key("os", config=config1)

    config2 = Config(length_sort_straight=True)
    assert ":" in module_key("os", config=config2, straight_import=True)

    config3 = Config(length_sort_sections={"thirdparty"})
    assert ":" in module_key("os", config=config3, section_name="THIRDPARTY")


def test_module_key_force_to_top():
    config = Config(force_to_top=("top_mod",))
    
    res_top = module_key("top_mod", config=config)
    res_normal = module_key("normal_mod", config=config)
    
    assert res_top.startswith("A")
    assert res_normal.startswith("B")
