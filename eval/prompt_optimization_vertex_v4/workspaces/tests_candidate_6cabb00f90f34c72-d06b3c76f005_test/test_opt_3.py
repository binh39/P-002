# file: src\sample_repo\isort\isort\wrap_modes.py:186-219
# asked: {"lines": [186, 187, 188, 190, 191, 192, 193, 194, 195, 197, 198, 199, 201, 202, 203, 204, 205, 207, 208, 210, 211, 212, 213, 214, 216, 217, 218, 219], "branches": [[187, 188], [187, 190], [201, 202], [201, 217], [205, 207], [205, 208], [208, 210], [208, 211], [211, 212], [211, 216], [217, 218], [217, 219]]}
# gained: {"lines": [186, 187, 188, 190, 191, 192, 193, 194, 195, 197, 198, 199, 201, 202, 203, 204, 205, 207, 208, 210, 211, 212, 213, 214, 216, 217, 218, 219], "branches": [[187, 188], [187, 190], [201, 202], [201, 217], [205, 207], [205, 208], [208, 210], [208, 211], [211, 212], [211, 216], [217, 218], [217, 219]]}

import pytest
from isort.wrap_modes import _vertical_grid_common

def test_vertical_grid_common_empty_imports():
    # Covers line 187-188: if not interface["imports"]: return ""
    result = _vertical_grid_common(
        need_trailing_char=False,
        imports=[],
        statement="from foo import",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        indent="    ",
        include_trailing_comma=False,
        line_length=80,
    )
    assert result == ""

def test_vertical_grid_common_basic_wrapping():
    # Covers lines 186-219 with various branches:
    # - comments addition
    # - while loop over imports
    # - current_line_length checks (exceeding line length vs not exceeding)
    # - include_trailing_comma handling
    result = _vertical_grid_common(
        need_trailing_char=True,
        imports=["bar", "baz", "very_long_import_name_that_exceeds_length_limit"],
        statement="from foo import",
        comments=["# comment"],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        indent="    ",
        include_trailing_comma=True,
        line_length=25,
    )
    assert isinstance(result, str)
    assert "bar" in result
    assert "baz" in result
    assert result.endswith(",")

def test_vertical_grid_common_no_trailing_comma_with_need_trailing_char():
    # Exercises branches where not interface["imports"] and need_trailing_char is True
    result = _vertical_grid_common(
        need_trailing_char=True,
        imports=["a", "b"],
        statement="from foo import",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        indent="    ",
        include_trailing_comma=False,
        line_length=5,
    )
    assert isinstance(result, str)
    assert "a" in result
    assert "b" in result
