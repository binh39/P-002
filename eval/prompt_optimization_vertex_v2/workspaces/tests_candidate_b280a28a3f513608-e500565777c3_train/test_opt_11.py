# file: src\sample_repo\isort\isort\wrap_modes.py:271-308
# asked: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}
# gained: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}

import pytest
from isort.wrap_modes import vertical_prefix_from_module_import

def test_vertical_prefix_from_module_import_empty_imports():
    result = vertical_prefix_from_module_import(
        imports=[],
        statement="from my_module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_length=80,
        line_separator="\n",
    )
    assert result == ""

def test_vertical_prefix_from_module_import_basic():
    # Covers normal flow, loop execution, line length not exceeded, and final comments check
    result = vertical_prefix_from_module_import(
        imports=["a", "b"],
        statement="from my_module import ",
        comments=["# comment"],
        remove_comments=False,
        comment_prefix="#",
        line_length=80,
        line_separator="\n",
    )
    assert "a" in result
    assert "b" in result

def test_vertical_prefix_from_module_import_exceeds_line_length():
    # Forces the line length check inside the loop to trigger and wrap,
    # and tests the branch where comments and statement_with_comments are truthy at the end.
    result = vertical_prefix_from_module_import(
        imports=["a", "b", "c"],
        statement="from my_module import ",
        comments=["# note"],
        remove_comments=False,
        comment_prefix="#",
        line_length=25,  # small line length to trigger line length condition
        line_separator="\n",
    )
    assert isinstance(result, str)
    assert "a" in result
    assert "b" in result
    assert "c" in result
    assert "\n" in result
