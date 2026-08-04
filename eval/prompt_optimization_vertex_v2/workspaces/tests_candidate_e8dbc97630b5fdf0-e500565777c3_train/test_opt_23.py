# file: src\sample_repo\isort\isort\literal.py:39-71
# asked: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}
# gained: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66]]}

import pytest
import ast
from isort.literal import assignment, type_mapping
from isort.exceptions import LiteralParsingFailure, LiteralSortTypeMismatch
from isort.settings import Config


def test_assignment_sort_type_assignments():
    code = "b = 2\na = 1\n"
    res = assignment(code, "assignments", ".py")
    assert "a = 1" in res


def test_assignment_unknown_sort_type():
    with pytest.raises(ValueError, match="Trying to sort using an undefined sort_type"):
        assignment("x = [1, 2]", "unknown_type", ".py")


def test_assignment_parsing_failure():
    valid_type = list(type_mapping.keys())[0]
    with pytest.raises(LiteralParsingFailure):
        assignment("x = invalid_literal_expression_syntax", valid_type, ".py")


def test_assignment_type_mismatch():
    first_key = list(type_mapping.keys())[0]
    expected_type, _ = type_mapping[first_key]
    
    other_val = 123 if expected_type is not int else ["a"]
    
    with pytest.raises(LiteralSortTypeMismatch):
        assignment(f"x = {other_val!r}", first_key, ".py")


def test_assignment_success_and_formatting():
    valid_type = None
    for k, (t, _) in type_mapping.items():
        if t is list:
            valid_type = k
            break
    if not valid_type:
        valid_type = list(type_mapping.keys())[0]

    expected_type, _ = type_mapping[valid_type]
    
    sample_data = {
        list: "[2, 1]",
        dict: "{'b': 2, 'a': 1}",
        tuple: "(2, 1)",
        set: "{2, 1}"
    }.get(expected_type, "[2, 1]")

    code = f"my_var = {sample_data}   \n"

    def dummy_formatting(code_str: str, extension: str, config: Config) -> str:
        return code_str + " # formatted"

    config = Config(formatting_function=dummy_formatting)
    res = assignment(code, valid_type, ".py", config=config)
    assert "# formatted" in res
    assert res.endswith("\n")
