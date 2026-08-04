# file: src\sample_repo\isort\isort\literal.py:39-71
# asked: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}
# gained: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66]]}

import pytest
import ast
from isort.literal import assignment, type_mapping
from isort.exceptions import LiteralParsingFailure, LiteralSortTypeMismatch
from isort.settings import DEFAULT_CONFIG, Config


def test_assignment_sort_type_assignments():
    res = assignment("b = 2\na = 1\n", "assignments", "py", DEFAULT_CONFIG)
    assert res == "a = 1\nb = 2\n"


def test_assignment_invalid_sort_type():
    with pytest.raises(ValueError) as exc_info:
        assignment("x = [1, 2]", "nonexistent_type", "py", DEFAULT_CONFIG)
    assert "Trying to sort using an undefined sort_type" in str(exc_info.value)


def test_assignment_parsing_failure():
    with pytest.raises(LiteralParsingFailure):
        assignment("x = [1, ", "tuple", "py", DEFAULT_CONFIG)


def test_assignment_sort_type_mismatch():
    # 'tuple' expects a tuple, but we pass a list
    with pytest.raises(LiteralSortTypeMismatch):
        assignment("x = [1, 2]", "tuple", "py", DEFAULT_CONFIG)


def test_assignment_success_and_formatting():
    valid_sort_type = None
    for st, (expected_t, _) in type_mapping.items():
        if expected_t is list:
            valid_sort_type = st
            break
    
    if not valid_sort_type:
        valid_sort_type = list(type_mapping.keys())[0]

    expected_type, _ = type_mapping[valid_sort_type]

    if expected_type is list:
        code = "x = [2, 1]   "
    elif expected_type is tuple:
        code = "x = (2, 1)   "
    elif expected_type is dict:
        code = "x = {'b': 2, 'a': 1}"
    elif expected_type is set:
        code = "x = {2, 1}"
    else:
        code = f"x = {expected_type()}"

    def dummy_formatter(code_str, ext, cfg):
        return code_str + " # formatted"

    config_with_formatter = Config(formatting_function=dummy_formatter)

    res = assignment(code, valid_sort_type, "py", config_with_formatter)
    assert res.endswith("   ") or " # formatted" in res
