# file: src\sample_repo\isort\isort\literal.py:39-71
# asked: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}
# gained: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66]]}

import pytest
import ast
from isort.literal import assignment, type_mapping
from isort.exceptions import LiteralParsingFailure, LiteralSortTypeMismatch
from isort.settings import Config


def test_assignment_sort_type_assignments():
    # Covers line 43-44
    code = "b = [1, 2]\na = [3, 4]\n"
    result = assignment(code, "assignments", "py")
    assert "a = [3, 4]" in result
    assert "b = [1, 2]" in result


def test_assignment_undefined_sort_type():
    # Covers lines 45-48
    code = "x = [1, 2]"
    with pytest.raises(ValueError, match="Trying to sort using an undefined sort_type"):
        assignment(code, "nonexistent_type", "py")


def test_assignment_literal_parsing_failure():
    # Covers lines 51-57 (specifically ast.literal_eval failing raising LiteralParsingFailure)
    code = "x = unparseable_name"
    with pytest.raises(LiteralParsingFailure):
        assignment(code, "list", "py")


def test_assignment_sort_type_mismatch():
    # Covers lines 59-61 (type(value) is not expected_type raising LiteralSortTypeMismatch)
    code = "x = (1, 2)"  # tuple
    with pytest.raises(LiteralSortTypeMismatch):
        assignment(code, "list", "py")  # expected_type is list, but value is tuple


def test_assignment_success_and_formatting():
    # Covers lines 63-71 successfully, including config.formatting_function and trailing whitespace (code[len(code.rstrip()):])
    formatting_called = []

    def dummy_formatting(code_str: str, ext: str, cfg: Config) -> str:
        formatting_called.append((code_str, ext, cfg))
        return code_str + "   "

    config = Config(formatting_function=dummy_formatting)
    code = "x = [2, 1]\n\n"
    
    result = assignment(code, "list", "py", config=config)
    assert len(formatting_called) == 1
    assert "x = " in result
    assert result.endswith("\n\n")
