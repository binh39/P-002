# file: src\sample_repo\isort\isort\wrap_modes.py:47-85
# asked: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}
# gained: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}

import pytest
from isort.wrap_modes import grid

def test_grid_empty_imports():
    result = grid(
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
    assert result == ""

def test_grid_single_import_no_wrap():
    result = grid(
        imports=["a"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_length=80,
        line_separator="\n",
        white_space="    ",
        include_trailing_comma=False,
    )
    assert result == "from module import (a)"

def test_grid_multiple_imports_no_wrap():
    result = grid(
        imports=["a", "b", "c"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_length=80,
        line_separator="\n",
        white_space="    ",
        include_trailing_comma=True,
    )
    assert result == "from module import (a, b, c,)"

def test_grid_exceeds_line_length_triggers_wrap_and_inner_wrap():
    # This test triggers:
    # 1. line length exceeded for `next_statement` (lines 61-62)
    # 2. inner multi-part `next_import` splitting (lines 66-72) where some parts fit and some exceed line length
    result = grid(
        imports=["a", "very_long_import_name_that_forces_wrapping part1 part2 part3"],
        statement="from m import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_length=30,
        line_separator="\n",
        white_space="    ",
        include_trailing_comma=True,
    )
    assert "from m import (a," in result
    assert "very_long_import_name_that_forces_wrapping" in result
    assert result.endswith(")")
