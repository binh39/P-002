# file: src\sample_repo\isort\isort\literal.py:39-71
# asked: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}
# gained: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66]]}

import pytest
import ast
from isort.exceptions import LiteralParsingFailure, LiteralSortTypeMismatch
from isort.literal import assignment
from isort.settings import Config


def test_assignment_sort_type_assignments():
    # Covers line 43-44: if sort_type == "assignments": return assignments(code)
    # Since 'assignments' parses multiple assignment lines or similar, let's see how assignments function works or mock/test it.
    # Wait, let's test what assignments(code) expects or if a simple string works.
    code = "a = [2, 1]\nb = [4, 3]"
    res = assignment(code, "assignments", "py")
    assert res is not None


def test_assignment_unknown_sort_type():
    # Covers lines 45-48: if sort_type not in type_mapping: raise ValueError(...)
    with pytest.raises(ValueError, match="Trying to sort using an undefined sort_type"):
        assignment("x = [1, 2]", "unknown_type", "py")


def test_assignment_literal_parsing_failure():
    # Covers lines 54-57: try ast.literal_eval except Exception -> LiteralParsingFailure
    with pytest.raises(LiteralParsingFailure):
        assignment("x = invalid_syntax_literal", "list", "py")


def test_assignment_sort_type_mismatch():
    # Covers lines 60-61: if type(value) is not expected_type: raise LiteralSortTypeMismatch
    # 'list' expects a list, but we pass a dict
    with pytest.raises(LiteralSortTypeMismatch):
        assignment("x = {'a': 1}", "list", "py")


def test_assignment_success_and_formatting_and_trailing_whitespace():
    # Covers lines 51-53, 59, 63-64, 65-67 (with formatting_function), 70-71 (trailing whitespace/newlines)
    formatting_called = []

    def mock_formatting(code_str, ext, cfg):
        formatting_called.append((code_str, ext, cfg))
        return code_str

    config = Config(formatting_function=mock_formatting)

    # Include trailing newline/whitespace to hit code[len(code.rstrip()):]
    code = "my_var = [2, 1]   \n\n"
    res = assignment(code, "list", "py", config=config)

    assert formatting_called
    assert "my_var =" in res
    assert res.endswith("\n\n")
