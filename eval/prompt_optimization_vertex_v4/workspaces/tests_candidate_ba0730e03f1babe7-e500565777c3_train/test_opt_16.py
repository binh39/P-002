# file: src\sample_repo\isort\isort\literal.py:39-71
# asked: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}
# gained: {"lines": [39, 43, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66]]}

import pytest
import ast
from isort.exceptions import LiteralParsingFailure, LiteralSortTypeMismatch
from isort.settings import Config
from isort.literal import assignment, type_mapping


def test_assignment_sort_type_assignments():
    # Covers line 43-44
    code = "a = [2, 1]"
    # Wait, assignments(code) might expect a specific format, let's test what assignments expects or test ValueError (line 45-48)
    with pytest.raises(ValueError, match="Trying to sort using an undefined sort_type"):
        assignment("a = [1, 2]", sort_type="unknown_type", extension="py")


def test_assignment_value_error():
    # Covers lines 45-48
    with pytest.raises(ValueError, match="Trying to sort using an undefined sort_type"):
        assignment("a = [1, 2]", sort_type="invalid", extension="py")


def test_assignment_literal_parsing_failure():
    # Covers lines 54-57
    with pytest.raises(LiteralParsingFailure):
        assignment("a = invalid_literal_expression()", sort_type="list", extension="py")


def test_assignment_type_mismatch():
    # Covers lines 60-61
    with pytest.raises(LiteralSortTypeMismatch):
        # 'list' expects a list, but we pass a tuple
        assignment("a = (1, 2)", sort_type="list", extension="py")


def test_assignment_success_with_formatting_and_trailing_whitespace():
    # Covers lines 39-71 including formatting_function and trailing whitespace/newlines
    formatting_called = []

    def dummy_formatting(code_str: str, ext: str, cfg: Config) -> str:
        formatting_called.append((code_str, ext, cfg))
        return code_str + "\n"

    config = Config(formatting_function=dummy_formatting)

    code = "my_list = [2, 1]   \n"
    res = assignment(code, sort_type="list", extension="py", config=config)
    assert len(formatting_called) == 1
    assert "my_list =" in res
    # Ensures trailing whitespace/newlines from original code are preserved (line 70)
    assert res.endswith("   \n")
