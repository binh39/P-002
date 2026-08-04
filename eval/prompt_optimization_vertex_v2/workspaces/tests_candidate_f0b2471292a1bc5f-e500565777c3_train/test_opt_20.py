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
    res = assignment(code, sort_type="assignments", extension="py")
    assert "a = 1" in res


def test_assignment_undefined_sort_type():
    with pytest.raises(ValueError, match="Trying to sort using an undefined sort_type"):
        assignment("a = [1, 2]", sort_type="unknown_type", extension="py")


def test_assignment_parsing_failure():
    with pytest.raises(LiteralParsingFailure):
        assignment("a = invalid_literal_syntax", sort_type="tuple", extension="py")


def test_assignment_sort_type_mismatch():
    # 'tuple' expects a tuple, but we provide a list
    with pytest.raises(LiteralSortTypeMismatch):
        assignment("a = [1, 2]", sort_type="tuple", extension="py")


def test_assignment_success_and_formatting_and_trailing_whitespace():
    # Find a valid sort_type from type_mapping
    # Let's inspect type_mapping keys to pick one (e.g. 'tuple' or 'dict' or 'list')
    valid_sort_type = next(iter(type_mapping.keys()))
    expected_type, _ = type_mapping[valid_sort_type]

    # Construct a valid literal matching expected_type
    if expected_type is list:
        val_str = "[2, 1]"
    elif expected_type is dict:
        val_str = "{'b': 2, 'a': 1}"
    elif expected_type is tuple:
        val_str = "(2, 1)"
    elif expected_type is set:
        val_str = "{2, 1}"
    else:
        # Fallback if there's any other type
        val_str = repr(expected_type())

    code = f"my_var = {val_str}   \n"

    # Define a custom formatting function to exercise config.formatting_function branch
    def dummy_formatting_fn(code_str, ext, cfg):
        return code_str.upper()

    config = Config(formatting_function=dummy_formatting_fn)

    res = assignment(code, sort_type=valid_sort_type, extension="py", config=config)
    assert isinstance(res, str)
    # Ensure trailing whitespace from code[len(code.rstrip()):] is preserved at the end
    assert res.endswith("\n")
