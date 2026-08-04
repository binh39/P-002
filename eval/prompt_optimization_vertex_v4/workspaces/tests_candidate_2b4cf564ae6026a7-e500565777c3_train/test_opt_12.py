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
    # Covers basic execution of the loop and `else` branch (lines 84)
    # and trailing comma handling.
    result = grid(
        imports=["import a", "import b"],
        statement="from module import ",
        line_length=80,
        line_separator="\n",
        white_space="    ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        include_trailing_comma=True,
    )
    assert result == "from module import (import a, import b,)"


def test_grid_long_line_wrap():
    # Covers the `if` branch (lines 61-82) where `next_statement` exceeds line_length.
    # Also covers the loop over parts in next_import (lines 66-71) where new_line fits or doesn't fit.
    result = grid(
        imports=["import a", "very_long_import_name_that_forces_wrapping_and_splitting_across_lines as alias"],
        statement="from module import ",
        line_length=30,
        line_separator="\n",
        white_space="    ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        include_trailing_comma=False,
    )
    # This should trigger line length checks, wrapping, and splitting parts.
    assert "very_long_import_name_that_forces_wrapping_and_splitting_across_lines" in result
    assert result.endswith(")")


def test_grid_long_line_part_wrap():
    # Specifically tests inner loop over parts (lines 66-71) where `new_line` exceeds line_length
    # to hit `lines.append(f"{interface['white_space']}{part}")` (line 68-69)
    # as well as `else` branch (line 70-71).
    result = grid(
        imports=["import a", "part1 part2 part3 part4"],
        statement="from module import ",
        line_length=15,
        line_separator="\n",
        white_space="    ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        include_trailing_comma=True,
    )
    assert "part1" in result
    assert "part2" in result
    assert result.endswith(")")
