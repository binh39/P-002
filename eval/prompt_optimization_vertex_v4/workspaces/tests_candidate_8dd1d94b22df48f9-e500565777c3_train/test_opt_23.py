# file: src\sample_repo\isort\isort\literal.py:39-71
# asked: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}
# gained: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}

import pytest
import ast
from isort.literal import assignment
from isort.exceptions import LiteralParsingFailure, LiteralSortTypeMismatch
from isort.settings import DEFAULT_CONFIG, Config


def test_assignment_sort_type_assignments():
    code = "b = 1\na = 2\n"
    res = assignment(code, "assignments", "py")
    assert res == "a = 2\nb = 1\n"


def test_assignment_undefined_sort_type():
    with pytest.raises(ValueError, match="Trying to sort using an undefined sort_type"):
        assignment("x = [2, 1]", "non_existent_type", "py")


def test_assignment_parsing_failure():
    with pytest.raises(LiteralParsingFailure):
        assignment("x = unparsable_syntax_abc_xyz", "tuple", "py")


def test_assignment_type_mismatch():
    # 'tuple' expected_type is tuple, but we pass a list
    with pytest.raises(LiteralSortTypeMismatch):
        assignment("x = [2, 1]", "tuple", "py")


def test_assignment_success_and_formatting():
    # Success path for 'tuple', plus trailing whitespace and optional formatting function
    code = "x = (2, 1)  \n"
    res = assignment(code, "tuple", "py", config=DEFAULT_CONFIG)
    assert "x = " in res
    assert res.endswith("  \n")

    # Now with a formatting_function in config
    def dummy_formatter(code_str, extension, cfg):
        return code_str.upper()

    custom_config = Config(formatting_function=dummy_formatter)
    res_formatted = assignment("x = (2, 1)  \n", "tuple", "py", config=custom_config)
    assert res_formatted.startswith("X =")
    assert res_formatted.endswith("  \n")
