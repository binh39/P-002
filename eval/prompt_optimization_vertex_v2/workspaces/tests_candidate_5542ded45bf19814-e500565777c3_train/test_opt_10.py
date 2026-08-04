# file: src\sample_repo\isort\isort\wrap_modes.py:47-85
# asked: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}
# gained: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69]]}

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

def test_grid_simple_flow():
    interface = {
        "imports": ["a", "b"],
        "statement": "from module import ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 80,
        "white_space": "    ",
        "include_trailing_comma": True,
    }
    res = grid(**interface)
    assert res == "from module import (a, b,)"

def test_grid_wrap_long_line_and_long_import_part():
    # This test triggers the line length overflow branch and multi-part import wrapping
    interface = {
        # First pop(0) leaves "as_very_long_name_import_1", then we have a multi-word import that exceeds line_length when combined or when parts are added.
        "imports": ["as_very_long_name_import_1", "import_part1 import_part2_very_long_name_that_forces_wrapping"],
        "statement": "from module import ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 25,
        "white_space": "    ",
        "include_trailing_comma": False,
    }
    res = grid(**interface)
    assert "from module import" in res
    assert "import_part1" in res
