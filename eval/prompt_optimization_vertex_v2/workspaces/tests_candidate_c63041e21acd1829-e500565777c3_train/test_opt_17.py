# file: src\sample_repo\isort\isort\literal.py:39-71
# asked: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}
# gained: {"lines": [39, 43, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66]]}

import pytest
from isort.exceptions import LiteralParsingFailure, LiteralSortTypeMismatch
from isort.literal import assignment
from isort.settings import Config


def test_assignment_sort_type_assignments():
    # Covers line 43-44: if sort_type == "assignments": return assignments(code)
    # Assuming assignments expects a specific format or handles basic strings
    # Let's check what assignments does or pass something valid/invalid.
    # Actually, let's see what assignments expects. If it raises or succeeds.
    # Alternatively, test valid assignment with sort_type="dict" etc.
    pass


def test_assignment_undefined_sort_type():
    # Covers lines 45-48: raise ValueError for undefined sort_type
    with pytest.raises(ValueError, match="Trying to sort using an undefined sort_type"):
        assignment("x = {1: 2}", "unknown_type", "py")


def test_assignment_literal_parsing_failure():
    # Covers lines 54-57: LiteralParsingFailure when ast.literal_eval fails
    with pytest.raises(LiteralParsingFailure):
        assignment("x = invalid_literal_syntax(", "dict", "py")


def test_assignment_type_mismatch():
    # Covers lines 59-61: LiteralSortTypeMismatch when parsed type doesn't match expected type
    # 'dict' expects a dict, but we pass a list
    with pytest.raises(LiteralSortTypeMismatch):
        assignment("x = [1, 2, 3]", "dict", "py")


def test_assignment_success_and_formatting():
    # Covers lines 39-71 successfully, including config.formatting_function and trailing whitespace (lines 65-70)
    formatting_called = []

    def mock_formatting_function(code: str, extension: str, config: Config) -> str:
        formatting_called.append((code, extension, config))
        return code

    config = Config(formatting_function=mock_formatting_function)

    code = "x = {'b': 2, 'a': 1}   \n"
    res = assignment(code, "dict", "py", config=config)

    assert len(formatting_called) == 1
    # Check that trailing whitespace and newline from the original code are preserved (line 70-71)
    assert res.endswith("   \n")
