# file: src\sample_repo\isort\isort\literal.py:39-71
# asked: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}
# gained: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}

import pytest
import ast
from isort.literal import assignment
from isort.exceptions import LiteralParsingFailure, LiteralSortTypeMismatch
from isort.settings import DEFAULT_CONFIG, Config

def test_assignment_sort_type_assignments():
    code = "b = 2\na = 1"
    res2 = assignment(code, "assignments", "py")
    assert "a = 1" in res2

def test_assignment_invalid_sort_type():
    with pytest.raises(ValueError, match="Trying to sort using an undefined sort_type"):
        assignment("a = [1, 2]", "invalid_type", "py")

def test_assignment_literal_parsing_failure():
    with pytest.raises(LiteralParsingFailure):
        assignment("a = invalid_syntax_literal", "tuple", "py")

def test_assignment_sort_type_mismatch():
    # 'tuple' expects a tuple, but we pass a list
    with pytest.raises(LiteralSortTypeMismatch):
        assignment("a = [1, 2]", "tuple", "py")

def test_assignment_success_and_formatting():
    # Let's test a valid tuple sorting
    code = "a = (2, 1)  \n"
    # 'tuple' maps to tuple type and a sorting function
    res = assignment(code, "tuple", "py")
    assert isinstance(res, str)

def test_assignment_with_formatting_function():
    def custom_formatter(code_str, ext, cfg):
        return code_str + " # formatted"
    
    config = Config(formatting_function=custom_formatter)
    code = "a = (2, 1)\n"
    res = assignment(code, "tuple", "py", config=config)
    assert "# formatted" in res
