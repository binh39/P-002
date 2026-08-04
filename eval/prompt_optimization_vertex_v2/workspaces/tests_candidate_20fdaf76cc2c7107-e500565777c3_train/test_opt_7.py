# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

import pytest
from isort.settings import Config
from isort.sorting import module_key


def test_module_key_match_reverse_relative():
    config = Config(reverse_relative=True)
    res = module_key(".foo", config)
    assert res == "B. foo"


def test_module_key_match_normal_relative():
    config = Config(reverse_relative=False)
    res = module_key("..bar", config)
    assert res == "B.._bar"


def test_module_key_ignore_case_true():
    config = Config(case_sensitive=True)
    res = module_key("FOO", config, ignore_case=True)
    assert res == "Bfoo"


def test_module_key_ignore_case_false():
    config = Config(case_sensitive=True)
    res = module_key("FOO", config, ignore_case=False)
    assert res == "BFOO"


def test_module_key_sub_imports_order_by_type_constants():
    config = Config(order_by_type=True, constants=["my_const"], case_sensitive=True)
    res = module_key("my_const", config, sub_imports=True)
    assert res == "BAmy_const"


def test_module_key_sub_imports_order_by_type_classes():
    config = Config(order_by_type=True, classes=["MyClass"], case_sensitive=True)
    res = module_key("MyClass", config, sub_imports=True)
    assert res == "BBMyClass"


def test_module_key_sub_imports_order_by_type_variables():
    config = Config(order_by_type=True, variables=["my_var"], case_sensitive=True)
    res = module_key("my_var", config, sub_imports=True)
    assert res == "BCmy_var"


def test_module_key_sub_imports_order_by_type_isupper():
    config = Config(order_by_type=True, case_sensitive=True)
    res = module_key("ABC", config, sub_imports=True)
    assert res == "BAABC"


def test_module_key_sub_imports_order_by_type_classes_or_isupper_first_char():
    config = Config(order_by_type=True, classes=[], case_sensitive=True)
    res = module_key("Abc", config, sub_imports=True)
    assert res == "BBAbc"


def test_module_key_sub_imports_order_by_type_else():
    config = Config(order_by_type=True, case_sensitive=True)
    res = module_key("abc", config, sub_imports=True)
    assert res == "BCabc"


def test_module_key_case_sensitive_false():
    config = Config(case_sensitive=False)
    res = module_key("FOO", config)
    assert res == "Bfoo"


def test_module_key_length_sort_config():
    config = Config(length_sort=True, case_sensitive=True)
    res = module_key("foo", config)
    assert res == "B3:foo"


def test_module_key_length_sort_straight():
    config = Config(length_sort_straight=True, case_sensitive=True)
    res = module_key("foo", config, straight_import=True)
    assert res == "B3:foo"


def test_module_key_length_sort_sections():
    config = Config(length_sort_sections={"sec"}, case_sensitive=True)
    res = module_key("foo", config, section_name="SEC")
    assert res == "B3:foo"


def test_module_key_force_to_top():
    config = Config(force_to_top=["foo"], case_sensitive=True)
    res = module_key("foo", config)
    assert res == "Afoo"
