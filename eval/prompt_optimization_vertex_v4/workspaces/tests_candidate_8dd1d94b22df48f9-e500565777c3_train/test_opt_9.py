# file: src\sample_repo\isort\isort\wrap_modes.py:47-85
# asked: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}
# gained: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69]]}

import pytest
from isort.wrap_modes import grid


def test_grid_empty_imports():
    # Covers line 49-50: if not interface["imports"]: return ""
    result = grid(imports=[])
    assert result == ""


def test_grid_simple_wrap():
    # Covers basic execution of grid mode without exceeding line length
    interface = {
        "imports": ["a", "b"],
        "statement": "from module import ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 80,
        "include_trailing_comma": False,
        "white_space": "    ",
    }
    result = grid(**interface)
    assert result == "from module import (a, b)"


def test_grid_line_length_exceeded_and_multiline_import():
    # This test exercises:
    # 1. Exceeding line_length inside the while loop (lines 61-63 -> True)
    # 2. Wrapping parts of next_import when it contains spaces (lines 65-72)
    #    - specifically hitting both branches of line 68 (new_line length > line_length vs <= line_length)
    # 3. Trailing comma handling (line 85)
    interface = {
        "imports": [
            "first_import",
            "a_very_long_import_name_that_should_wrap_across_multiple_lines with_subparts",
        ],
        "statement": "import ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 25,
        "include_trailing_comma": True,
        "white_space": "    ",
    }
    result = grid(**interface)
    assert "import (first_import," in result
    assert "    a_very_long_import_name_that_should_wrap_across_multiple_lines" in result
    assert "    with_subparts" in result
    assert result.endswith(")")


def test_grid_line_length_exceeded_short_parts():
    # Exercises line 68 where new_line length + 1 <= line_length (the else branch of line 68)
    interface = {
        "imports": [
            "first",
            "short part1 part2",
        ],
        "statement": "import ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 15,
        "include_trailing_comma": False,
        "white_space": "    ",
    }
    result = grid(**interface)
    assert "import (first," in result
    assert result.endswith(")")
