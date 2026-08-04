# file: src\sample_repo\isort\isort\literal.py:39-71
# asked: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}
# gained: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66]]}

import pytest
from isort.exceptions import LiteralParsingFailure, LiteralSortTypeMismatch
from isort.literal import assignment
from isort.settings import Config


def test_assignment_sort_type_assignments():
    # Covers line 43-44: sort_type == "assignments"
    code = "x = 1"
    # assignments(code) or similar behavior
    res = assignment(code, "assignments", "py")
    assert isinstance(res, str)


def test_assignment_invalid_sort_type():
    # Covers lines 45-48: sort_type not in type_mapping -> ValueError
    with pytest.raises(ValueError, match="Trying to sort using an undefined sort_type"):
        assignment("x = [1, 2]", "invalid_type", "py")


def test_assignment_literal_parsing_failure():
    # Covers lines 54-57: ast.literal_eval fails -> LiteralParsingFailure
    with pytest.raises(LiteralParsingFailure):
        assignment("x = invalid_syntax_literal(", "list", "py")


def test_assignment_type_mismatch():
    # Covers lines 60-61: type(value) is not expected_type -> LiteralSortTypeMismatch
    # 'list' expects a list, but we pass a dict
    with pytest.raises(LiteralSortTypeMismatch):
        assignment("x = {'a': 1}", "list", "py")


def test_assignment_success_and_formatting_function():
    # Covers lines 63-71 successfully, including config.formatting_function and trailing whitespace
    formatting_called = []

    def mock_formatting(code_str: str, ext: str, cfg: Config) -> str:
        formatting_called.append((code_str, ext, cfg))
        return code_str + "   "

    config = Config(formatting_function=mock_formatting)

    code = "my_list = [2, 1]   \n"
    res = assignment(code, "list", "py", config=config)

    assert len(formatting_called) == 1
    # Check that trailing whitespace from original code is preserved (lines 70-71)
    assert res.endswith("\n")
    assert "my_list =" in res
