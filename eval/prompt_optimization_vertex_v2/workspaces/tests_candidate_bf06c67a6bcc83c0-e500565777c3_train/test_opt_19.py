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
    res = assignment(code, "assignments", "py")
    assert "a = 1" in res

def test_assignment_invalid_sort_type():
    with pytest.raises(ValueError, match="Trying to sort using an undefined sort_type"):
        assignment("a = [1, 2]", "nonexistent_sort_type", "py")

def test_assignment_parsing_failure():
    with pytest.raises(LiteralParsingFailure):
        assignment("a = invalid_syntax_literal(", "list", "py")

def test_assignment_sort_type_mismatch():
    # 'list' expects a list, but we provide a dict or int
    with pytest.raises(LiteralSortTypeMismatch):
        assignment("a = {'key': 1}", "list", "py")

def test_assignment_success_and_formatting():
    # Valid list sorting with formatting function and trailing whitespace/newlines
    formatting_called = []
    def dummy_formatting(code_str, ext, cfg):
        formatting_called.append((code_str, ext, cfg))
        return code_str.strip()

    config = Config(formatting_function=dummy_formatting)
    code = "a = [2, 1]   \n\n"
    res = assignment(code, "list", "py", config=config)
    assert len(formatting_called) == 1
    assert "a = [1, 2]" in res
    # Ensure trailing whitespace/newlines are preserved at the end
    assert res.endswith("\n\n")
