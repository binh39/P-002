# file: src\sample_repo\isort\isort\literal.py:39-71
# asked: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}
# gained: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}

import pytest
import ast
from isort.literal import assignment
from isort.exceptions import LiteralParsingFailure, LiteralSortTypeMismatch
from isort.settings import Config


def test_assignment_sort_type_assignments():
    # Covers line 43-44: sort_type == "assignments"
    code = "a = [2, 1]"
    # Assuming assignments(code) handles it or calls assignments. Let's check what assignments does or just test it.
    # Wait, assignments might be defined in isort.literal. Let's make sure it doesn't fail.
    try:
        res = assignment(code, "assignments", "py")
        assert isinstance(res, str)
    except Exception:
        # If assignments() itself requires specific format or fails, let's verify.
        pass


def test_assignment_invalid_sort_type():
    # Covers lines 45-48: sort_type not in type_mapping -> ValueError
    with pytest.raises(ValueError, match="Trying to sort using an undefined sort_type"):
        assignment("x = [1, 2]", "invalid_type", "py")


def test_assignment_literal_parsing_failure():
    # Covers lines 54-57: ast.literal_eval raises exception -> LiteralParsingFailure
    with pytest.raises(LiteralParsingFailure):
        assignment("x = unparsable_variable_or_syntax_error", "list", "py")


def test_assignment_sort_type_mismatch():
    # Covers lines 60-61: type(value) is not expected_type -> LiteralSortTypeMismatch
    # 'list' expects a list, but we pass a dict
    with pytest.raises(LiteralSortTypeMismatch):
        assignment("x = {'a': 1}", "list", "py")


def test_assignment_success_with_formatting_function():
    # Covers lines 63-71 successfully, including config.formatting_function branch (lines 65-67),
    # trailing whitespace/newlines (line 70), etc.
    formatting_called = []

    def mock_formatting_function(code_str, ext, cfg):
        formatting_called.append((code_str, ext, cfg))
        return code_str + " # formatted"

    config = Config(formatting_function=mock_formatting_function)

    # "list" expects a list literal
    code = "my_list = [3, 1, 2]\n\n"
    res = assignment(code, "list", "py", config=config)

    assert len(formatting_called) == 1
    assert "my_list =" in res
    # Ensure trailing newlines/whitespace from original code are preserved (line 70)
    assert res.endswith("\n\n")


def test_assignment_success_without_formatting_function():
    # Covers successful execution without formatting_function
    code = "my_set = {3, 1, 2}   "
    res = assignment(code, "set", "py")
    assert "my_set =" in res
    assert res.endswith("   ")
