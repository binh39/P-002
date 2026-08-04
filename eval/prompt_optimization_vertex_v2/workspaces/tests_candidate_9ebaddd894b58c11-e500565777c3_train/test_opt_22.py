# file: src\sample_repo\isort\isort\literal.py:39-71
# asked: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}
# gained: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}

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
        assignment("x = [1, 2]", "nonexistent_type", "py")


def test_assignment_literal_parsing_failure():
    with pytest.raises(LiteralParsingFailure):
        assignment("x = invalid_python_syntax(", "list", "py")


def test_assignment_type_mismatch():
    # 'list' expects a list, but we provide a dict or int
    with pytest.raises(LiteralSortTypeMismatch):
        assignment("x = {'a': 1}", "list", "py")


def test_assignment_success_and_formatting():
    # Success case for 'list'
    code = "x = [3, 1, 2]\n"
    res = assignment(code, "list", "py")
    assert res is not None

    # Success case with formatting function and trailing whitespace/newlines
    def dummy_formatting(code_str, ext, cfg):
        return code_str.upper()

    config = Config(formatting_function=dummy_formatting)
    code_with_trailing = "x = [3, 1, 2]   \n\n"
    res2 = assignment(code_with_trailing, "list", "py", config=config)
    assert res2 is not None
    assert "\n\n" in res2
