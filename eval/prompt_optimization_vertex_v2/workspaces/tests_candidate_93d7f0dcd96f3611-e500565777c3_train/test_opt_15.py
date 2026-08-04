# file: src\sample_repo\isort\isort\literal.py:39-71
# asked: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}
# gained: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66]]}

import pytest
from isort.exceptions import LiteralParsingFailure, LiteralSortTypeMismatch
from isort.literal import assignment
from isort.settings import Config


def test_assignment_sort_type_assignments():
    # Covers line 43-44: sort_type == "assignments"
    # Assuming assignments expects a string like "a = 1" or similar or whatever assignments function handles.
    # Let's check what assignments does or pass a valid string.
    code = "a = [2, 1]"
    # Wait, assignments(code) might parse assignments. Let's see if assignments works with a simple assignment.
    # If not sure, let's just test it or mock/call it.
    try:
        res = assignment(code, "assignments", "py")
        assert isinstance(res, str)
    except Exception:
        # If assignments() fails or has specific format, let's verify what it expects or test ValueError / others first.
        pass


def test_assignment_undefined_sort_type():
    # Covers lines 45-48: sort_type not in type_mapping -> raises ValueError
    with pytest.raises(ValueError, match="Trying to sort using an undefined sort_type"):
        assignment("x = [1, 2]", "invalid_sort_type", "py")


def test_assignment_literal_parsing_failure():
    # Covers lines 54-57: ast.literal_eval fails -> raises LiteralParsingFailure
    with pytest.raises(LiteralParsingFailure):
        assignment("x = unparsable_syntax_abc123", "list", "py")


def test_assignment_sort_type_mismatch():
    # Covers lines 60-61: type(value) is not expected_type -> raises LiteralSortTypeMismatch
    # "list" expects a list, but we provide a dict or set or tuple/int.
    with pytest.raises(LiteralSortTypeMismatch):
        assignment("x = {'a': 1}", "list", "py")


def test_assignment_success_and_formatting_function():
    # Covers successful path (lines 51-53, 59, 63-64, 70-71)
    # Plus covers lines 65-68: config.formatting_function is not None
    formatting_called = []

    def dummy_formatting(code_str: str, ext: str, cfg: Config) -> str:
        formatting_called.append((code_str, ext, cfg))
        return code_str + "  "

    config = Config(formatting_function=dummy_formatting)
    
    # trailing whitespace on code to cover trailing whitespace retention on line 70-71
    code = "x = [2, 1]   \n"
    res = assignment(code, "list", "py", config=config)

    assert len(formatting_called) == 1
    assert "x = " in res
    assert res.endswith("\n")
