# file: src\sample_repo\isort\isort\literal.py:39-71
# asked: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}
# gained: {"lines": [39, 43, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66]]}

import pytest
import ast
from isort.exceptions import LiteralParsingFailure, LiteralSortTypeMismatch
from isort.literal import assignment
from isort.settings import Config


def test_assignment_invalid_sort_type():
    with pytest.raises(ValueError, match="Trying to sort using an undefined sort_type"):
        assignment("x = [1, 2]", "invalid_type", "py")


def test_assignment_literal_parsing_failure():
    with pytest.raises(LiteralParsingFailure):
        assignment("x = unparsable_literal_syntax(", "list", "py")


def test_assignment_type_mismatch():
    with pytest.raises(LiteralSortTypeMismatch):
        # 'list' expects a list, but we give a dict
        assignment("x = {'a': 1}", "list", "py")


def test_assignment_success_and_formatting():
    # Test successful sorting with list, formatting function, and trailing whitespace/newlines
    formatted_called = []

    def dummy_formatting(code: str, extension: str, config: Config) -> str:
        formatted_called.append((code, extension, config))
        return code + " # formatted"

    config = Config(formatting_function=dummy_formatting)
    code = "x = [2, 1]\n"
    
    res = assignment(code, "list", "py", config=config)
    
    assert len(formatted_called) == 1
    assert "x = " in res
    assert res.endswith("\n")
