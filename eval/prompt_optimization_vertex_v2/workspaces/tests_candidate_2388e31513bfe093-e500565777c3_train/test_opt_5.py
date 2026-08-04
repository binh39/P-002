# file: src\sample_repo\isort\isort\wrap_modes.py:47-85
# asked: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}
# gained: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69]]}

import pytest
from isort.wrap_modes import grid


def test_grid_empty_imports():
    interface = {
        "imports": [],
        "statement": "from module import ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 80,
        "white_space": "    ",
        "include_trailing_comma": False,
    }
    assert grid(**interface) == ""


def test_grid_single_import_no_trailing_comma():
    interface = {
        "imports": ["a"],
        "statement": "from module import ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 80,
        "white_space": "    ",
        "include_trailing_comma": False,
    }
    assert grid(**interface) == "from module import (a)"


def test_grid_multiple_imports_within_line_length():
    interface = {
        "imports": ["a", "b", "c"],
        "statement": "from module import ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 80,
        "white_space": "    ",
        "include_trailing_comma": True,
    }
    assert grid(**interface) == "from module import (a, b, c,)"


def test_grid_exceeds_line_length_triggers_wrap():
    interface = {
        "imports": ["a", "very_long_import_name_that_exceeds_the_line_limit"],
        "statement": "from module import ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 30,
        "white_space": "    ",
        "include_trailing_comma": False,
    }
    result = grid(**interface)
    assert "from module import (a,\n    very_long_import_name_that_exceeds_the_line_limit)" in result


def test_grid_long_import_parts_wrap():
    interface = {
        "imports": ["a", "part1 part2 part3"],
        "statement": "from module import ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 15,
        "white_space": "    ",
        "include_trailing_comma": False,
    }
    result = grid(**interface)
    # Testing that 'part1 part2 part3' internal spaces trigger line_length checks within the part loop
    assert result is not None
    assert "part1" in result
    assert "part2" in result
    assert "part3" in result


def test_grid_long_import_parts_exceed_line_length():
    interface = {
        "imports": ["a", "longword1 longword2 longword3"],
        "statement": "from module import ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 12,
        "white_space": "    ",
        "include_trailing_comma": True,
    }
    result = grid(**interface)
    assert result is not None
    assert "longword1" in result
    assert "longword2" in result
    assert "longword3" in result
