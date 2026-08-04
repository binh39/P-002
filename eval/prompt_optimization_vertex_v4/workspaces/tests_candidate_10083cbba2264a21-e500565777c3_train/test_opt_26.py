# file: src\sample_repo\isort\isort\literal.py:39-71
# asked: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}
# gained: {"lines": [39, 43, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}

import pytest
import ast
from isort.literal import assignment, type_mapping, assignments
from isort.exceptions import LiteralParsingFailure, LiteralSortTypeMismatch
from isort.settings import Config




def test_assignment_undefined_sort_type():
    # Covers lines 45-48
    code = "a = [1, 2]"
    with pytest.raises(ValueError, match="Trying to sort using an undefined sort_type"):
        assignment(code, "unknown_type", ".py")


def test_assignment_literal_parsing_failure():
    # Covers lines 54-57
    code = "a = invalid_syntax_literal"
    with pytest.raises(LiteralParsingFailure):
        assignment(code, "list", ".py")


def test_assignment_type_mismatch():
    # Covers lines 60-61
    code = "a = (1, 2)"  # tuple, but sort_type is "list"
    with pytest.raises(LiteralSortTypeMismatch):
        assignment(code, "list", ".py")


def test_assignment_success_and_formatting():
    # Covers lines 39-71 successfully (list, dict, etc.) with and without formatting_function and trailing whitespace/newlines
    code = "my_list = [2, 1]   \n"
    
    # Without formatting function
    result = assignment(code, "list", ".py")
    assert "my_list =" in result
    assert result.endswith("\n")

    # With formatting function
    def dummy_formatting(code_str: str, ext: str, cfg: Config) -> str:
        return code_str.upper()

    config = Config(formatting_function=dummy_formatting)
    result_formatted = assignment(code, "list", ".py", config=config)
    assert "MY_LIST =" in result_formatted
    assert result_formatted.endswith("\n")
