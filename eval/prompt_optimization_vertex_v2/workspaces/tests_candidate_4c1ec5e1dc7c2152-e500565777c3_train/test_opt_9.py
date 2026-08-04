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
        line_length=80,
        line_separator="\n",
        white_space="    ",
        include_trailing_comma=False,
    )
    assert result == ""


def test_grid_single_import():
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


def test_grid_wrap_long_next_statement():
    # Forces `len(next_statement.split(interface["line_separator"])[-1]) + 1 > interface["line_length"]`
    result = grid(
        imports=["a", "very_long_import_name_that_exceeds_line_length"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_length=20,
        line_separator="\n",
        white_space="    ",
        include_trailing_comma=False,
    )
    assert "very_long_import_name_that_exceeds_line_length" in result


def test_grid_wrap_long_next_import_parts():
    # Forces wrapping inside the `for part in next_import.split(" ")[1:]:` loop
    # i.e., both the `len(new_line) + 1 > interface["line_length"]` being True and False.
    result = grid(
        imports=["a", "multi part import name that is extremely long"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_length=15,
        line_separator="\n",
        white_space="    ",
        include_trailing_comma=True,
    )
    assert "multi" in result
    assert "import" in result
