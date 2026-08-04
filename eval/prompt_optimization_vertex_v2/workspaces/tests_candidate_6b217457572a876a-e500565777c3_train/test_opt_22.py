# file: src\sample_repo\isort\isort\literal.py:39-71
# asked: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}
# gained: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66]]}

import pytest
import ast
from isort.literal import assignment, type_mapping
from isort.exceptions import LiteralParsingFailure, LiteralSortTypeMismatch
from isort.settings import Config


def test_assignment_sort_type_assignments():
    code = "b = 2\na = 1"
    res = assignment(code, "assignments", "py")
    assert "a = 1" in res


def test_assignment_invalid_sort_type():
    with pytest.raises(ValueError, match="Trying to sort using an undefined sort_type"):
        assignment("x = [1, 2]", "nonexistent_sort_type", "py")


def test_assignment_parsing_failure():
    with pytest.raises(LiteralParsingFailure):
        assignment("x = invalid_literal_expression(", "tuple", "py")


def test_assignment_type_mismatch():
    if "tuple" in type_mapping:
        with pytest.raises(LiteralSortTypeMismatch):
            assignment("x = [1, 2]", "tuple", "py")


def test_assignment_success_and_formatting_function():
    sort_type = None
    for k, (exp_type, _) in type_mapping.items():
        if exp_type is list:
            sort_type = k
            break
    if not sort_type:
        sort_type = list(type_mapping.keys())[0]

    expected_type, _ = type_mapping[sort_type]
    
    if expected_type is list:
        lit = "[2, 1]"
    elif expected_type is tuple:
        lit = "(2, 1)"
    elif expected_type is dict:
        lit = "{'b': 2, 'a': 1}"
    elif expected_type is set:
        lit = "{2, 1}"
    else:
        lit = "1"

    code = f"x = {lit}  \n"

    def dummy_formatting_fn(code_str, ext, cfg):
        return code_str + " # formatted"

    config = Config(formatting_function=dummy_formatting_fn)

    res = assignment(code, sort_type, "py", config=config)
    assert "# formatted" in res
    assert res.endswith("\n")
