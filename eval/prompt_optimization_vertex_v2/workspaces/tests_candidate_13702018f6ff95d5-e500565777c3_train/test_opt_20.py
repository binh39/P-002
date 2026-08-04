# file: src\sample_repo\isort\isort\literal.py:39-71
# asked: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}
# gained: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}

import pytest
import ast
from isort.exceptions import LiteralParsingFailure, LiteralSortTypeMismatch, AssignmentsFormatMismatch
from isort.literal import assignment, type_mapping
from isort.settings import Config


def test_assignment_sort_type_assignments():
    # Covers line 43-44: sort_type == "assignments"
    # Pass valid input for `assignments` function
    code = "b = 2\na = 1\n"
    res = assignment(code, "assignments", "py")
    assert "a = 1" in res


def test_assignment_invalid_sort_type():
    # Covers lines 45-48: sort_type not in type_mapping
    with pytest.raises(ValueError, match="Trying to sort using an undefined sort_type"):
        assignment("x = [1, 2]", "nonexistent_type", "py")


def test_assignment_literal_parsing_failure():
    # Covers lines 54-57: ast.literal_eval fails raising LiteralParsingFailure
    with pytest.raises(LiteralParsingFailure):
        assignment("x = invalid_syntax_or_name", "list", "py")


def test_assignment_type_mismatch():
    # Covers lines 60-61: type(value) is not expected_type
    # 'list' expects list, but we provide a dict or int
    with pytest.raises(LiteralSortTypeMismatch):
        assignment("x = {'a': 1}", "list", "py")


def test_assignment_success_and_formatting():
    # Covers lines 39-71 successfully, including config.formatting_function and trailing whitespace (code[len(code.rstrip()):])
    formatting_called = []

    def mock_formatting_function(code_str, ext, cfg):
        formatting_called.append((code_str, ext, cfg))
        return code_str

    config = Config(formatting_function=mock_formatting_function)

    code = "x = [2, 1]   "
    res = assignment(code, "list", "py", config=config)
    
    assert formatting_called
    assert res.endswith("   ")


def test_assignment_success_without_formatting_function():
    # Covers success path without formatting_function
    config = Config()
    code = "x = [2, 1]"
    res = assignment(code, "list", "py", config=config)
    assert "x = " in res
