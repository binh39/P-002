# file: src\sample_repo\isort\isort\literal.py:39-71
# asked: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}
# gained: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66]]}

import pytest
import ast
from isort.literal import assignment, type_mapping
from isort.exceptions import LiteralParsingFailure, LiteralSortTypeMismatch
from isort.settings import DEFAULT_CONFIG, Config


def test_assignment_sort_type_assignments():
    code = "a = 1\nb = 2\n"
    res = assignment(code, sort_type="assignments", extension="py")
    assert res == "a = 1\nb = 2\n"


def test_assignment_invalid_sort_type():
    with pytest.raises(ValueError) as exc_info:
        assignment("x = [1, 2]", sort_type="nonexistent_type", extension="py")
    assert "Trying to sort using an undefined sort_type" in str(exc_info.value)


def test_assignment_literal_parsing_failure():
    with pytest.raises(LiteralParsingFailure):
        assignment("x = [1, 2", sort_type="tuple", extension="py")


def test_assignment_type_mismatch():
    # 'tuple' expected type is tuple, but we pass a list
    with pytest.raises(LiteralSortTypeMismatch):
        assignment("x = [1, 2]", sort_type="tuple", extension="py")


def test_assignment_success_and_formatting():
    # Find a valid sort_type from type_mapping
    sort_type = next(iter(type_mapping.keys()))
    expected_type, _ = type_mapping[sort_type]

    # Construct a valid literal of expected_type
    if expected_type is list:
        lit_code = "x = [2, 1]"
    elif expected_type is dict:
        lit_code = "x = {'b': 2, 'a': 1}"
    elif expected_type is tuple:
        lit_code = "x = (2, 1)"
    elif expected_type is set:
        lit_code = "x = {2, 1}"
    else:
        # Fallback if there's any other type
        return

    # Define a custom formatting function to test config.formatting_function branch
    def dummy_formatter(code_str, ext, cfg):
        return code_str + " # formatted"

    config = Config(formatting_function=dummy_formatter)

    res = assignment(lit_code + "   \n", sort_type=sort_type, extension="py", config=config)
    assert "# formatted" in res
    # Ensure trailing whitespace/newlines from original code are preserved at the end
    assert res.endswith("   \n")
