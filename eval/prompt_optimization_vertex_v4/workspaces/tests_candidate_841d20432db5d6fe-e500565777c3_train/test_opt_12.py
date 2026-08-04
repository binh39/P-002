# file: src\sample_repo\isort\isort\wrap_modes.py:47-85
# asked: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}
# gained: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69]]}

import pytest
from isort.wrap_modes import grid

def test_grid_empty_imports():
    result = grid(
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
    assert result == ""

def test_grid_no_line_length_exceeded():
    result = grid(
        imports=["a", "b", "c"],
        statement="from module import",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
        white_space="    ",
        include_trailing_comma=True,
    )
    assert result == "from module import(a, b, c,)"

def test_grid_line_length_exceeded_with_parts_fitting_and_exceeding():
    # Trigger the `if len(next_statement.split(...) ...)` branch (lines 61-82)
    # Also trigger the inner loop (lines 66-71) where `new_line` exceeds line length (lines 68-69) vs fits (lines 70-71).
    result = grid(
        imports=["alpha beta", "gamma delta epsilon zeta"],
        statement="from module import",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=15,
        white_space="    ",
        include_trailing_comma=False,
    )
    assert "alpha" in result
    assert "beta" in result
    assert "gamma" in result
    assert "delta" in result
