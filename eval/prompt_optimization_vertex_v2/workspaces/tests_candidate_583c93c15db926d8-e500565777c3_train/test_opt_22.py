# file: src\sample_repo\isort\isort\literal.py:39-71
# asked: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}
# gained: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66]]}

import pytest
import ast
from isort.literal import assignment
from isort.exceptions import LiteralParsingFailure, LiteralSortTypeMismatch
from isort.settings import Config


def test_assignment_sort_type_assignments():
    code = "b = 2\na = 1\n"
    res = assignment(code, "assignments", ".py")
    assert "a = 1" in res


def test_assignment_unknown_sort_type():
    with pytest.raises(ValueError, match="Trying to sort using an undefined sort_type"):
        assignment("x = [1, 2]", "unknown_type", ".py")


def test_assignment_parsing_failure():
    with pytest.raises(LiteralParsingFailure):
        assignment("x = [1, ", "list", ".py")


def test_assignment_type_mismatch():
    with pytest.raises(LiteralSortTypeMismatch):
        assignment("x = (1, 2)", "list", ".py")


def test_assignment_success_with_formatting_and_trailing_whitespace():
    def mock_formatting(code_str, ext, cfg):
        return code_str + " # formatted"

    config = Config(formatting_function=mock_formatting)
    code = "x = [2, 1]   \n"
    res = assignment(code, "list", ".py", config=config)
    assert "# formatted" in res
    assert res.endswith("\n")
