# file: src\sample_repo\isort\isort\literal.py:39-71
# asked: {"lines": [39, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 63, 64, 65, 66, 67, 68, 70, 71], "branches": [[43, 44], [43, 45], [45, 46], [45, 51], [60, 61], [60, 63], [65, 66], [65, 70]]}
# gained: {"lines": [39, 43, 45, 46, 47, 48], "branches": [[43, 45], [45, 46]]}

import ast
import pytest
from isort.exceptions import LiteralParsingFailure, LiteralSortTypeMismatch
from isort.settings import DEFAULT_CONFIG, Config
from isort.literal import assignment

# Mocking the type_mapping and assignments function for testing purposes
type_mapping = {
    "lists": (list, sorted),
    "tuples": (tuple, sorted),
    "dicts": (dict, lambda x, _: dict(sorted(x.items()))),
    "unique-list": (list, lambda x, _: sorted(set(x))),
    "unique-tuple": (tuple, lambda x, _: tuple(sorted(set(x)))),
    "set": (set, sorted),
}




def test_assignment_invalid_sort_type():
    code = "my_var = 42"
    sort_type = "invalid_type"
    with pytest.raises(ValueError, match="Trying to sort using an undefined sort_type"):
        assignment(code, sort_type, "")


