# file: src\sample_repo\isort\isort\literal.py:39-71
# asked: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}
# gained: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66]]}

import pytest
import ast
from isort.literal import assignment, type_mapping
from isort.exceptions import LiteralParsingFailure, LiteralSortTypeMismatch
from isort.settings import Config


def test_assignment_sort_type_assignments():
    code = "b = 2\na = 1\n"
    res = assignment(code, "assignments", ".py")
    assert "a = 1" in res


def test_assignment_undefined_sort_type():
    with pytest.raises(ValueError, match="Trying to sort using an undefined sort_type"):
        assignment("x = [1, 2]", "nonexistent_type", ".py")


def test_assignment_literal_parsing_failure():
    with pytest.raises(LiteralParsingFailure):
        # invalid python literal syntax for literal_eval
        assignment("x = invalid_syntax_here", list(type_mapping.keys())[0], ".py")


def test_assignment_type_mismatch():
    # pick the first key from type_mapping (e.g., 'tuple' or 'list' or 'dict' or 'set')
    # and pass the wrong type (e.g. dict when list is expected)
    sort_type = list(type_mapping.keys())[0]
    expected_type, _ = type_mapping[sort_type]
    
    # Find a different type
    wrong_value = 123 if expected_type is not int else "string"
    
    with pytest.raises(LiteralSortTypeMismatch):
        assignment(f"x = {wrong_value!r}", sort_type, ".py")


def test_assignment_success_and_formatting_and_trailing_whitespace():
    sort_type = list(type_mapping.keys())[0]
    expected_type, _ = type_mapping[sort_type]

    # Create valid literal for expected_type
    if expected_type is list:
        val = [2, 1]
    elif expected_type is dict:
        val = {"b": 2, "a": 1}
    elif expected_type is set:
        val = {2, 1}
    elif expected_type is tuple:
        val = (2, 1)
    else:
        # fallback or construct based on type
        val = expected_type()

    def dummy_formatting_function(code, extension, config):
        return code.strip() + " # formatted"

    config = Config(formatting_function=dummy_formatting_function)

    code = f"x = {val!r}   \n"
    res = assignment(code, sort_type, ".py", config=config)
    assert "# formatted" in res
    assert res.endswith("\n")
