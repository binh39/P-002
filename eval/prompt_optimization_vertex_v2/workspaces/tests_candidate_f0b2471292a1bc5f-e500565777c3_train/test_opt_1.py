# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

import pytest
from isort.settings import Config
from isort.sorting import module_key


def test_module_key_relative_and_ignore_case():
    config = Config(reverse_relative=True, case_sensitive=True)
    # relative import matching re.match(r"^(\.+)\s*(.*)", module_name)
    # reverse_relative=True -> sep = " "
    # ignore_case=False branch (else branch)
    key = module_key(".foo", config, ignore_case=False)
    assert isinstance(key, str)

    # reverse_relative=False -> sep = "_"
    config_rev = Config(reverse_relative=False, case_sensitive=True)
    key_rev = module_key(".. bar", config_rev, ignore_case=False)
    assert "_" in key_rev

    # ignore_case=True branch
    key_ignore = module_key(".FOO", config, ignore_case=True)
    assert isinstance(key_ignore, str)


def test_module_key_order_by_type_branches():
    # Test all branches inside sub_imports and config.order_by_type
    config = Config(
        order_by_type=True,
        constants=["CONST"],
        classes=["MyClass"],
        variables=["my_var"],
        case_sensitive=True,
    )

    # 1. module_name in config.constants -> prefix = "A"
    assert "A" in module_key("CONST", config, sub_imports=True)

    # 2. module_name in config.classes -> prefix = "B"
    assert "B" in module_key("MyClass", config, sub_imports=True)

    # 3. module_name in config.variables -> prefix = "C"
    assert "C" in module_key("my_var", config, sub_imports=True)

    # 4. module_name.isupper() and len(module_name) > 1 -> prefix = "A"
    assert "A" in module_key("SOME_OTHER_CONST", config, sub_imports=True)

    # 5. module_name in config.classes or module_name[0:1].isupper() -> prefix = "B"
    assert "B" in module_key("UppercaseName", config, sub_imports=True)

    # 6. else branch -> prefix = "C"
    assert "C" in module_key("lowercase_name", config, sub_imports=True)


def test_module_key_case_sensitive_and_length_sort():
    # case_sensitive = False -> module_name.lower()
    config_case = Config(case_sensitive=False)
    key_case = module_key("FOO", config_case)
    assert "foo" in key_case

    # length_sort combinations:
    # config.length_sort = True
    config_ls1 = Config(length_sort=True)
    key_ls1 = module_key("foo", config_ls1)
    assert "3:foo" in key_ls1

    # config.length_sort_straight and straight_import = True
    config_ls2 = Config(length_sort_straight=True)
    key_ls2 = module_key("foo", config_ls2, straight_import=True)
    assert "3:foo" in key_ls2

    # str(section_name).lower() in config.length_sort_sections
    config_ls3 = Config(length_sort_sections={"thirdparty"})
    key_ls3 = module_key("foo", config_ls3, section_name="THIRDPARTY")
    assert "3:foo" in key_ls3


def test_module_key_force_to_top():
    config_top = Config(force_to_top=["topmod"], case_sensitive=True)
    key_top = module_key("topmod", config_top)
    # Starts with 'A' because it's in force_to_top
    assert key_top.startswith("A")

    config_normal = Config(force_to_top=[], case_sensitive=True)
    key_normal = module_key("normalmod", config_normal)
    # Starts with 'B' because it's not in force_to_top
    assert key_normal.startswith("B")
