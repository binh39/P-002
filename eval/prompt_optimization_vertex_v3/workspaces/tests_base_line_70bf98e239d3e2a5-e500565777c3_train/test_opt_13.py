# file: src\sample_repo\isort\isort\wrap_modes.py:47-85
# asked: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}
# gained: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}

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


def test_grid_basic_no_wrap():
    # Covers: imports with multiple items fitting within line_length
    result = grid(
        imports=["a", "b", "c"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
        white_space="    ",
        include_trailing_comma=True,
    )
    assert result == "from module import (a, b, c,)"


def test_grid_wrap_import():
    # Forces the `if len(next_statement.split(...) ... ) > line_length:` branch (lines 61-82)
    # Also tests multi-part import wrapping (lines 65-72)
    result = grid(
        imports=["short", "very_long_import_name_that_exceeds_length"],
        statement="from module import",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=20,
        white_space="    ",
        include_trailing_comma=False,
    )
    assert "very_long_import_name_that_exceeds_length" in result
    assert result.startswith("from module import(short,\n")


def test_grid_wrap_import_multiple_parts_splitting():
    # Exercises wrapping where next_import has multiple space-separated parts 
    # and some parts exceed the line length individually or cumulatively (lines 66-71).
    result = grid(
        imports=["foo", "as_very_long_alias_name foo bar baz"],
        statement="from module import",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=15,
        white_space="    ",
        include_trailing_comma=True,
    )
    assert result.endswith(")")
    assert "\n" in result
