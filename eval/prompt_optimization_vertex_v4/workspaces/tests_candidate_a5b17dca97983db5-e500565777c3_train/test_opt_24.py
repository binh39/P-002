# file: src\sample_repo\isort\isort\literal.py:39-71
# asked: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}
# gained: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}

import pytest
import ast
from isort.literal import assignment, type_mapping
from isort.exceptions import LiteralParsingFailure, LiteralSortTypeMismatch
from isort.settings import Config


def test_assignment_sort_type_assignments():
    code = "b = 2\na = 1"
    res = assignment(code, "assignments", "py")
    assert res is not None


def test_assignment_invalid_sort_type():
    with pytest.raises(ValueError):
        assignment("a = [1, 2]", "invalid_sort_type", "py")


def test_assignment_parsing_failure():
    with pytest.raises(LiteralParsingFailure):
        assignment("a = invalid_syntax_here!", "tuple", "py")


def test_assignment_type_mismatch():
    sort_type_key = next(iter(type_mapping.keys()))
    expected_type, _ = type_mapping[sort_type_key]
    
    if expected_type is tuple:
        wrong_val = "[1, 2]"
    else:
        wrong_val = "(1, 2)"

    with pytest.raises(LiteralSortTypeMismatch):
        assignment(f"a = {wrong_val}", sort_type_key, "py")


def test_assignment_success_and_formatting():
    for sort_type, (exp_type, _) in type_mapping.items():
        if exp_type is list:
            code = "my_list = [2, 1]\n"
            res = assignment(code, sort_type, "py")
            assert "my_list =" in res
            break
        elif exp_type is dict:
            code = "my_dict = {'b': 2, 'a': 1}\n"
            res = assignment(code, sort_type, "py")
            assert "my_dict =" in res
            break
        elif exp_type is tuple:
            code = "my_tuple = (2, 1)\n"
            res = assignment(code, sort_type, "py")
            assert "my_tuple =" in res
            break
        elif exp_type is set:
            code = "my_set = {2, 1}\n"
            res = assignment(code, sort_type, "py")
            assert "my_set =" in res
            break


def test_assignment_with_formatting_function():
    def dummy_formatting(code: str, extension: str, config: Config) -> str:
        return code + " # formatted"

    config = Config(formatting_function=dummy_formatting)
    
    found_key = None
    for k, (t, _) in type_mapping.items():
        if t is list:
            found_key = k
            literal_str = "[2, 1]"
            break
    
    if found_key:
        code = f"x = {literal_str}   "
        res = assignment(code, found_key, "py", config=config)
        assert "# formatted" in res
        assert res.endswith("   ")
