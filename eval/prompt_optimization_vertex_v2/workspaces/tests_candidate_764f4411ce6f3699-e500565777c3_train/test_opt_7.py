# file: src\sample_repo\isort\isort\wrap_modes.py:47-85
# asked: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}
# gained: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69]]}

import pytest
from isort.wrap_modes import grid

def test_grid_empty_imports():
    res = grid(
        imports=[],
        statement="from module import",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
        white_space="    ",
        include_trailing_comma=False,
    )
    assert res == ""

def test_grid_no_wrap():
    res = grid(
        imports=["a", "b"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
        white_space="    ",
        include_trailing_comma=True,
    )
    assert res == "from module import (a, b,)"

def test_grid_wrap_simple_exceeds_line_length():
    res = grid(
        imports=["a", "very_long_import_name_that_exceeds_length"],
        statement="from module import ",
        comments=["# comment"],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=20,
        white_space="    ",
        include_trailing_comma=False,
    )
    assert "very_long_import_name_that_exceeds_length" in res

def test_grid_long_import_with_spaces_wrapping():
    res = grid(
        imports=["a", "import_part1 part2 part3"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=15,
        white_space="    ",
        include_trailing_comma=False,
    )
    assert "import_part1" in res
    assert "part2" in res
