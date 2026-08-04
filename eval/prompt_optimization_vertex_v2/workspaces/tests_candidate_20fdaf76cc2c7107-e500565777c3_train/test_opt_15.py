# file: src\sample_repo\isort\isort\wrap_modes.py:47-85
# asked: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}
# gained: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}

import pytest
from isort.wrap_modes import grid


def test_grid_empty_imports():
    interface = {
        "imports": [],
        "statement": "import a",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 80,
        "white_space": "    ",
        "include_trailing_comma": False,
    }
    assert grid(**interface) == ""


def test_grid_no_wrap():
    res = grid(
        imports=["b", "c"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
        white_space="    ",
        include_trailing_comma=True,
    )
    assert res == "from module import (b, c,)"


def test_grid_wrap_and_parts_wrapping():
    interface = {
        "imports": [
            "first",
            "very_long_import_name_that_forces_wrapping_and_has part2 part3"
        ],
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
    assert isinstance(res, str)
    assert "(" in res
    assert ")" in res
