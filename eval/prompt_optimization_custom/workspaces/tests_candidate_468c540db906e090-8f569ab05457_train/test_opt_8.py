# file: src\sample_repo\isort\isort\literal.py:39-71
# asked: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}
# gained: {"lines": [39, 43, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 70, 71], "branches": [[43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 70]]}

import ast
import pytest
from isort.exceptions import LiteralParsingFailure, LiteralSortTypeMismatch
from isort.settings import Config
from isort.literal import assignment  # Adjust the import based on your project structure

# Mocking the type_mapping and ISortPrettyPrinter for testing purposes
type_mapping = {
    "list": (list, lambda x, _: sorted(x)),
    "tuple": (tuple, lambda x, _: tuple(sorted(x))),
    "dict": (dict, lambda x, _: {k: x[k] for k in sorted(x)}),
    "unique-list": (list, lambda x, _: sorted(set(x))),
    "set": (set, lambda x, _: sorted(x)),
    "unique-tuple": (tuple, lambda x, _: tuple(sorted(set(x)))),
}

class MockISortPrettyPrinter:
    def __init__(self, config):
        self.config = config

def test_assignment_with_valid_list():
    code = "my_list = [3, 1, 2]"
    sort_type = "list"
    extension = ""
    config = Config()
    
    result = assignment(code, sort_type, extension, config)
    assert result == "my_list = [1, 2, 3]"

def test_assignment_with_valid_tuple():
    code = "my_tuple = (3, 1, 2)"
    sort_type = "tuple"
    extension = ""
    config = Config()
    
    result = assignment(code, sort_type, extension, config)
    assert result == "my_tuple = (1, 2, 3)"

def test_assignment_with_valid_dict():
    code = "my_dict = {'b': 1, 'a': 2}"
    sort_type = "dict"
    extension = ""
    config = Config()
    
    result = assignment(code, sort_type, extension, config)
    assert result == "my_dict = {'a': 2, 'b': 1}"

def test_assignment_with_invalid_sort_type():
    code = "my_var = 42"
    sort_type = "invalid_type"
    extension = ""
    config = Config()
    
    with pytest.raises(ValueError, match="Trying to sort using an undefined sort_type"):
        assignment(code, sort_type, extension, config)

def test_assignment_with_literal_parsing_failure():
    code = "my_var = [1, 2, 3"
    sort_type = "list"
    extension = ""
    config = Config()
    
    with pytest.raises(LiteralParsingFailure):
        assignment(code, sort_type, extension, config)

def test_assignment_with_type_mismatch():
    code = "my_var = 42"
    sort_type = "list"
    extension = ""
    config = Config()
    
    with pytest.raises(LiteralSortTypeMismatch):
        assignment(code, sort_type, extension, config)
