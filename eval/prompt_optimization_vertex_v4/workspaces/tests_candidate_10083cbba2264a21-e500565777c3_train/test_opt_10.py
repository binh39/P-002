# file: src\sample_repo\isort\isort\wrap_modes.py:47-85
# asked: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}
# gained: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}

import pytest
from isort.wrap_modes import grid


def test_grid_empty_imports():
    # Covers line 49-50: if not interface["imports"]: return ""
    result = grid(imports=[])
    assert result == ""


def test_grid_simple_wrap():
    # Covers normal flow where imports fit on one line and trailing comma is false
    result = grid(
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
    assert result == "from module import (a, b)"


def test_grid_include_trailing_comma():
    # Covers include_trailing_comma=True at line 85
    result = grid(
        imports=["a"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_length=80,
        line_separator="\n",
        white_space="    ",
        include_trailing_comma=True,
    )
    assert result == "from module import (a,)"


def test_grid_exceeds_line_length_and_parts_wrapping():
    # Covers lines 61-82 where next_statement exceeds line_length,
    # triggering the `lines` loop (lines 65-72) and part splitting where:
    # - len(new_line) + 1 > interface["line_length"] is True (line 68 -> 69)
    # - len(new_line) + 1 > interface["line_length"] is False (line 68 -> 71)
    result = grid(
        imports=["a", "very_long_import_name_that_needs_splitting part1 part2"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_length=30,
        line_separator="\n",
        white_space="    ",
        include_trailing_comma=False,
    )
    assert "(" in result
    assert ")" in result
    assert "very_long_import_name_that_needs_splitting" in result
    assert "part1" in result
    assert "part2" in result
