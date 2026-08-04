# file: src\sample_repo\isort\isort\literal.py:39-71
# asked: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}
# gained: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}

import pytest
import ast
from isort.exceptions import LiteralParsingFailure, LiteralSortTypeMismatch
from isort.literal import assignment
from isort.settings import Config


def test_assignment_sort_type_assignments():
    code = "x = [2, 1]"
    # sort_type == "assignments" returns assignments(code)
    # Let's test with a valid assignment or whatever assignments(code) handles,
    # or just test that it enters the first if branch.
    # Actually, assignments() might expect multiline or specific format,
    # let's check what assignments() does or just pass a simple string.
    res = assignment(code, "assignments", ".py")
    assert isinstance(res, str)


def test_assignment_invalid_sort_type():
    with pytest.raises(ValueError, match="Trying to sort using an undefined sort_type"):
        assignment("x = [1, 2]", "nonexistent", ".py")


def test_assignment_parsing_failure():
    with pytest.raises(LiteralParsingFailure):
        assignment("x = invalid_syntax_here_unparseable", "list", ".py")


def test_assignment_type_mismatch():
    with pytest.raises(LiteralSortTypeMismatch):
        # 'list' expects a list, but we provide a dict or int
        assignment("x = {1: 2}", "list", ".py")


def test_assignment_success_and_formatting():
    # Success case for 'list'
    code = "x = [2, 1]   \n"
    res = assignment(code, "list", ".py")
    assert "x = " in res
    assert res.endswith("\n")

    # Success case with a formatting_function configured
    def dummy_formatter(code_str, ext, cfg):
        return code_str + " # formatted"

    config = Config(formatting_function=dummy_formatter)
    res_fmt = assignment(code, "list", ".py", config=config)
    assert "# formatted" in res_fmt
