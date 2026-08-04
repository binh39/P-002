# file: src\sample_repo\isort\isort\literal.py:39-71
# asked: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}
# gained: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}

import pytest
import ast
from isort.literal import assignment
from isort.exceptions import LiteralParsingFailure, LiteralSortTypeMismatch
from isort.settings import Config

def test_assignment_sort_type_assignments():
    code = "b = 2\na = 1"
    res = assignment(code, "assignments", extension="py")
    assert "a = 1" in res

def test_assignment_invalid_sort_type():
    with pytest.raises(ValueError, match="Trying to sort using an undefined sort_type"):
        assignment("x = [1, 2]", "nonexistent_type", extension="py")

def test_assignment_literal_parsing_failure():
    with pytest.raises(LiteralParsingFailure):
        assignment("x = [unclosed_list", "list", extension="py")

def test_assignment_type_mismatch():
    with pytest.raises(LiteralSortTypeMismatch):
        # 'list' expects a list, but we pass a dict
        assignment("x = {'a': 1}", "list", extension="py")

def test_assignment_success_and_formatting():
    # Successful sorting of a list
    code = "x = [2, 1]   \n"
    res = assignment(code, "list", extension="py")
    assert "x = [1, 2]" in res

    # Test with formatting_function and trailing whitespace / newlines
    custom_config = Config(
        formatting_function=lambda code, ext, cfg: code + " # formatted"
    )
    code_with_trailing = "x = [2, 1]  \n\n"
    res2 = assignment(code_with_trailing, "list", extension="py", config=custom_config)
    assert "# formatted" in res2
    assert res2.endswith("\n\n")
