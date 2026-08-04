# file: src\sample_repo\isort\isort\wrap_modes.py:47-85
# asked: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}
# gained: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69]]}

import pytest
from isort.wrap_modes import grid

def test_grid_empty_imports():
    result = grid(imports=[])
    assert result == ""

def test_grid_normal_wrap():
    # Tests standard flow without exceeding line length, plus trailing comma branch
    result = grid(
        imports=["alpha", "beta"],
        statement="from module import ",
        comments={},
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=40,
        white_space="    ",
        include_trailing_comma=True,
    )
    assert result == "from module import (alpha, beta,)"

def test_grid_exceeds_line_length_and_long_import_parts():
    # Triggers line 61 (exceeding line length) and exercises splitting next_import into parts (lines 65-81)
    # where some parts fit on the same line and others trigger a new line (line 68).
    result = grid(
        imports=["short", "very_long_import_part1 part2_that_forces_a_wrap"],
        statement="import ",
        comments={},
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=15,
        white_space="    ",
        include_trailing_comma=False,
    )
    assert "(" in result
    assert ")" in result
