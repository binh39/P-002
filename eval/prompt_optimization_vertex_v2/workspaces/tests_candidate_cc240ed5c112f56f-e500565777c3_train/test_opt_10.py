# file: src\sample_repo\isort\isort\wrap_modes.py:47-85
# asked: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}
# gained: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69]]}

import pytest
from isort.wrap_modes import grid

def test_grid_empty_imports():
    interface = {
        "imports": [],
        "statement": "from module import ",
        "white_space": "    ",
        "indent": "    ",
        "line_length": 80,
        "comments": [],
        "line_separator": "\n",
        "comment_prefix": "#",
        "include_trailing_comma": False,
        "remove_comments": False,
    }
    assert grid(**interface) == ""

def test_grid_no_wrap():
    # Tests when imports fit in a single line (executes line 84: interface["statement"] += ", " + next_import)
    interface = {
        "imports": ["a", "b"],
        "statement": "from module import ",
        "white_space": "    ",
        "indent": "    ",
        "line_length": 80,
        "comments": [],
        "line_separator": "\n",
        "comment_prefix": "#",
        "include_trailing_comma": True,
        "remove_comments": False,
    }
    result = grid(**interface)
    assert result == "from module import (a, b,)"

def test_grid_wrap_long_import_and_line_splitting():
    # Tests wrapping triggered because line length exceeds limit (lines 61-82),
    # including multi-word import parts splitting and branch where new_line length exceeds line_length (lines 68-71)
    interface = {
        "imports": ["very_long_import_name_that_exceeds_length as short", "another_long_part_word1 word2"],
        "statement": "from module import ",
        "white_space": "    ",
        "indent": "    ",
        "line_length": 30,
        "comments": [],
        "line_separator": "\n",
        "comment_prefix": "#",
        "include_trailing_comma": False,
        "remove_comments": False,
    }
    result = grid(**interface)
    # Ensure it successfully formats and wraps without error
    assert "from module import (" in result
    assert "very_long_import_name_that_exceeds_length" in result
