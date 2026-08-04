# file: src\sample_repo\isort\isort\literal.py:39-71
# asked: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}
# gained: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66]]}

import pytest
import ast
from isort.exceptions import LiteralParsingFailure, LiteralSortTypeMismatch
from isort.settings import Config
from isort.literal import assignment

def test_assignment_sort_type_assignments():
    # Covers line 43-44
    code = "a = [2, 1]"
    # Assuming assignments(code) works or we can test it directly
    # Wait, assignments might sort list literals inside assignments. Let's see what assignments does or just call it.
    res = assignment(code, sort_type="assignments", extension=".py")
    assert isinstance(res, str)

def test_assignment_invalid_sort_type():
    # Covers lines 45-48
    with pytest.raises(ValueError, match="Trying to sort using an undefined sort_type"):
        assignment("a = [1, 2]", sort_type="invalid_type", extension=".py")

def test_assignment_literal_parsing_failure():
    # Covers lines 54-57
    with pytest.raises(LiteralParsingFailure):
        assignment("a = invalid_syntax_here", sort_type="list", extension=".py")

def test_assignment_type_mismatch():
    # Covers lines 60-61
    with pytest.raises(LiteralSortTypeMismatch):
        # sort_type 'dict' expects dict, but we pass a list
        assignment("a = [1, 2]", sort_type="dict", extension=".py")

def test_assignment_success_and_formatting():
    # Covers lines 39-71 (successful parsing, sorting, formatting_function, trailing whitespace)
    def dummy_formatting(code: str, extension: str, config: Config) -> str:
        return code.upper()

    config = Config(formatting_function=dummy_formatting)
    # code with trailing newline/whitespace to cover code[len(code.rstrip()):]
    code = "a = [2, 1]   \n"
    res = assignment(code, sort_type="list", extension=".py", config=config)
    assert isinstance(res, str)
    assert "A = " in res
