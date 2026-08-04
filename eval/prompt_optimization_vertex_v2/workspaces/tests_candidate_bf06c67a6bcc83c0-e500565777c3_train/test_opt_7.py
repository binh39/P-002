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

def test_grid_single_import_no_wrap():
    result = grid(
        imports=["a"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
        white_space="    ",
        include_trailing_comma=False,
    )
    assert result == "from module import (a)"

def test_grid_multiple_imports_no_wrap_with_trailing_comma():
    result = grid(
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
    assert result == "from module import (a, b,)"

def test_grid_exceeds_line_length_triggers_wrap():
    # Forces the branch where len(next_statement...) > interface["line_length"]
    result = grid(
        imports=["a", "very_long_import_name_that_forces_wrapping"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=20,
        white_space="    ",
        include_trailing_comma=False,
    )
    assert "(" in result
    assert ")" in result

def test_grid_multi_word_import_wrapping():
    # Triggers loops inside the wrapping logic where parts of next_import are split and wrapped
    result = grid(
        imports=["a", "some very long import alias as x"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=15,
        white_space="    ",
        include_trailing_comma=True,
    )
    assert "some" in result
    assert "alias" in result
