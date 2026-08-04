# file: src\sample_repo\isort\isort\literal.py:39-71
# asked: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}
# gained: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66]]}

import pytest
import ast
from isort.literal import assignment, type_mapping, assignments
from isort.exceptions import LiteralParsingFailure, LiteralSortTypeMismatch
from isort.settings import DEFAULT_CONFIG, Config


def test_assignment_sort_type_assignments():
    code = "a = 1\nb = 2\n"
    res = assignment(code, "assignments", "py", DEFAULT_CONFIG)
    assert res == assignments(code)


def test_assignment_undefined_sort_type():
    with pytest.raises(ValueError, match="Trying to sort using an undefined sort_type"):
        assignment("x = [1, 2]", "nonexistent_type", "py", DEFAULT_CONFIG)


def test_assignment_literal_parsing_failure():
    with pytest.raises(LiteralParsingFailure):
        assignment("x = unclosed_string", "tuple", "py", DEFAULT_CONFIG)


def test_assignment_type_mismatch():
    sort_type = next(iter(type_mapping.keys()))
    expected_type, _ = type_mapping[sort_type]
    
    if expected_type is tuple:
        val_str = "[1, 2]"
    else:
        val_str = "(1, 2)"

    with pytest.raises(LiteralSortTypeMismatch):
        assignment(f"x = {val_str}", sort_type, "py", DEFAULT_CONFIG)


def test_assignment_with_formatting_function_and_trailing_whitespace():
    sort_type = next(iter(type_mapping.keys()))
    expected_type, _ = type_mapping[sort_type]

    if expected_type is tuple:
        val_str = "(2, 1)"
    elif expected_type is list:
        val_str = "[2, 1]"
    elif expected_type is dict:
        val_str = "{'b': 2, 'a': 1}"
    elif expected_type is set:
        val_str = "{2, 1}"
    else:
        val_str = repr(expected_type())

    def custom_formatter(code_str, ext, cfg):
        return code_str + "  "

    config = Config(formatting_function=custom_formatter)

    code = f"x = {val_str}   \n"
    res = assignment(code, sort_type, "py", config)
    # The formatting function returns code_str + "  " but is `.rstrip()`ped by assignment line 66-67,
    # and then trailing whitespace of `code` (`code[len(code.rstrip()):]`) is appended back.
    assert res.endswith("   \n")
