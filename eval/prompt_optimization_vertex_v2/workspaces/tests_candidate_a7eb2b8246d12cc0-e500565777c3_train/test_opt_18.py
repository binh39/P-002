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
    res = assignment(code, sort_type="assignments", extension="py")
    assert "a = 1" in res


def test_assignment_invalid_sort_type():
    with pytest.raises(ValueError, match="Trying to sort using an undefined sort_type"):
        assignment("a = [1, 2]", sort_type="nonexistent", extension="py")


def test_assignment_literal_parsing_failure():
    with pytest.raises(LiteralParsingFailure):
        assignment("a = unparseable_literal(((", sort_type="list", extension="py")


def test_assignment_type_mismatch():
    with pytest.raises(LiteralSortTypeMismatch):
        # 'a' is a list, but sort_type is 'dict'
        assignment("a = [1, 2]", sort_type="dict", extension="py")


def test_assignment_success_with_formatting_function():
    def mock_formatting_function(code: str, extension: str, config: Config) -> str:
        return code + " # formatted"

    config = Config(formatting_function=mock_formatting_function)
    code = "a = [2, 1]\n"
    res = assignment(code, sort_type="list", extension="py", config=config)
    assert "# formatted" in res
    assert res.endswith("\n")


def test_assignment_success_without_formatting_function():
    config = Config(formatting_function=None)
    code = "a = [2, 1]"
    res = assignment(code, sort_type="list", extension="py", config=config)
    assert res.startswith("a =")
