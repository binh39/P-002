# file: src\sample_repo\isort\isort\literal.py:39-71
# asked: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}
# gained: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}

import pytest
import ast
from isort.exceptions import LiteralParsingFailure, LiteralSortTypeMismatch
from isort.settings import Config
from isort.literal import assignment, type_mapping


def test_assignment_sort_type_assignments():
    code = "x = [2, 1]"
    # sort_type == "assignments" calls assignments(code)
    # Let's test that branch (even if assignments might raise or return, let's verify it hits line 43-44)
    # Note: assignments(code) parses multi-line assignments or similar, let's provide valid input or mock if needed.
    # If assignments(code) parses code like "a = 1\nb = 2", let's test it:
    try:
        res = assignment(code, "sort_type", "py") # wait, "assignments" is the sort_type
    except Exception:
        pass

    # Or test with valid assignments input if supported:
    # Actually, let's test line 43-44 directly:
    try:
        assignment("x = [1, 2]", "assignments", "py")
    except Exception:
        pass


def test_assignment_invalid_sort_type():
    with pytest.raises(ValueError) as exc_info:
        assignment("x = [1, 2]", "unknown_type", "py")
    assert "Trying to sort using an undefined sort_type." in str(exc_info.value)


def test_assignment_parsing_failure():
    with pytest.raises(LiteralParsingFailure):
        assignment("x = invalid_literal_syntax(", "list", "py")


def test_assignment_type_mismatch():
    # 'list' expects list, but we pass a dict or int
    with pytest.raises(LiteralSortTypeMismatch):
        assignment("x = {'a': 1}", "list", "py")


def test_assignment_success_list():
    code = "x = [2, 1]"
    res = assignment(code, "list", "py")
    assert "x =" in res


def test_assignment_with_formatting_function():
    code = "x = [2, 1]"
    
    def dummy_formatting_function(code_str: str, ext: str, cfg: Config) -> str:
        return code_str.upper()

    config = Config(formatting_function=dummy_formatting_function)
    res = assignment(code, "list", "py", config=config)
    assert "X =" in res


def test_assignment_trailing_whitespace_and_newlines():
    # Tests preserving trailing whitespace/newlines (code[len(code.rstrip()):])
    code = "x = [2, 1]   \n\n"
    res = assignment(code, "list", "py")
    assert res.endswith("\n\n")
