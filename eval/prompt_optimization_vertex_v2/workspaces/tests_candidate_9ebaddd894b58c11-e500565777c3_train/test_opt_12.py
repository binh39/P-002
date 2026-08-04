# file: src\sample_repo\isort\isort\wrap_modes.py:47-85
# asked: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}
# gained: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69]]}

import pytest
from isort.wrap_modes import grid

def test_grid_empty_imports():
    res = grid(
        imports=[],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_length=80,
        line_separator="\n",
        white_space="    ",
        include_trailing_comma=False,
    )
    assert res == ""

def test_grid_normal_flow_no_wrap():
    res = grid(
        imports=["a", "b"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_length=80,
        line_separator="\n",
        white_space="    ",
        include_trailing_comma=False,
    )
    assert res == "from module import (a, b)"

def test_grid_wrap_branch_triggered():
    # This triggers the `if` branch where the line length exceeds line_length,
    # and also tests multi-word imports wrapping inside the inner for-loop (lines 66-71),
    # where some parts fit and some parts exceed the line length.
    res = grid(
        imports=["short", "verylongimportnamepart1 part2"],
        statement="from module import ",
        comments=["# comment"],
        remove_comments=False,
        comment_prefix="#",
        line_length=20,
        line_separator="\n",
        white_space="    ",
        include_trailing_comma=True,
    )
    assert isinstance(res, str)
    assert "short" in res
    assert "verylongimportnamepart1" in res
