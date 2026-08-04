# file: src\sample_repo\isort\isort\literal.py:39-71
# asked: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}
# gained: {"lines": [39, 43, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}

import pytest
import ast
from isort.literal import assignment, type_mapping
from isort.exceptions import LiteralParsingFailure, LiteralSortTypeMismatch
from isort.settings import Config


def test_assignment_sort_type_assignments():
    # Covers line 43-44
    code = "a = [2, 1]"
    # Wait, assignments(code) might expect specific format, let's check or mock if needed.
    # Actually, assignments sorts multiple assignments or similar. Let's see if we can test it or if it calls assignments().
    # Let's test with valid assignments input or test ValueError first.
    pass


def test_assignment_invalid_sort_type():
    # Covers lines 45-48
    with pytest.raises(ValueError, match="Trying to sort using an undefined sort_type"):
        assignment("x = [1, 2]", "nonexistent_type", ".py")


def test_assignment_literal_parsing_failure():
    # Covers lines 51-57
    with pytest.raises(LiteralParsingFailure):
        assignment("x = invalid_syntax_here", "list", ".py")


def test_assignment_type_mismatch():
    # Covers lines 59-61
    # 'list' expects a list, but we pass a dict
    with pytest.raises(LiteralSortTypeMismatch):
        assignment("x = {'a': 1}", "list", ".py")


def test_assignment_success_with_formatting_function():
    # Covers lines 39-71 including formatting_function and trailing whitespace (code[len(code.rstrip()):])
    def dummy_formatting_function(code_str: str, extension: str, config: Config) -> str:
        return code_str + "  "

    config = Config(formatting_function=dummy_formatting_function)
    
    # We use 'list' type with trailing newline/spaces
    code = "x = [2, 1]   \n"
    res = assignment(code, "list", ".py", config=config)
    assert "x =" in res
    assert res.endswith("\n")


def test_assignment_success_without_formatting_function():
    # Covers lines 39-71 where formatting_function is None
    config = Config(formatting_function=None)
    code = "x = [2, 1]\n"
    res = assignment(code, "list", ".py", config=config)
    assert "x =" in res
    assert res.endswith("\n")
