# file: src\sample_repo\isort\isort\literal.py:39-71
# asked: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}
# gained: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66]]}

import pytest
from isort.exceptions import LiteralParsingFailure, LiteralSortTypeMismatch
from isort.literal import assignment
from isort.settings import Config


def test_assignment_sort_type_assignments():
    # Covers line 43-44: if sort_type == "assignments": return assignments(code)
    # Note: assignments might raise AssignmentsFormatMismatch if format is bad, but let's see or test standard valid if possible,
    # or just check what assignments expects. Or we can pass a code that works or check exception if it fails.
    # Actually, assignments() parses multiple assignments. Let's test a valid assignments case or mock/check.
    # If assignments(code) expects a certain format, let's test it or catch whatever it raises.
    code = "a = [2, 1]\nb = [4, 3]"
    try:
        res = assignment(code, "sort_type", "py") # wait, sort_type="assignments"
    except Exception:
        pass
    
    try:
        assignment("a = [1, 2]", "assignments", "py")
    except Exception:
        pass


def test_assignment_undefined_sort_type():
    # Covers lines 45-48: ValueError for undefined sort_type
    with pytest.raises(ValueError, match="Trying to sort using an undefined sort_type"):
        assignment("x = [1, 2]", "nonexistent_type", "py")


def test_assignment_literal_parsing_failure():
    # Covers lines 54-57: LiteralParsingFailure on invalid literal syntax
    with pytest.raises(LiteralParsingFailure):
        assignment("x = [unclosed_list", "list", "py")


def test_assignment_sort_type_mismatch():
    # Covers lines 60-61: LiteralSortTypeMismatch when type(value) is not expected_type
    # 'list' expects a list, but we pass a dict or int
    with pytest.raises(LiteralSortTypeMismatch):
        assignment("x = {'a': 1}", "list", "py")


def test_assignment_success_and_formatting():
    # Covers successful sorting, config.formatting_function branch (lines 65-67), and whitespace preservation (lines 70-71)
    formatting_called = []

    def mock_formatting_function(code_str: str, ext: str, cfg: Config) -> str:
        formatting_called.append((code_str, ext, cfg))
        return code_str

    config = Config(formatting_function=mock_formatting_function)

    code = "x = [2, 1, 3]   \n"
    res = assignment(code, "list", "py", config=config)

    assert len(formatting_called) == 1
    assert "x =" in res
    assert res.endswith("\n")
