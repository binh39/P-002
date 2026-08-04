# file: src\sample_repo\isort\isort\wrap_modes.py:271-308
# asked: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}
# gained: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}

import pytest
from isort.wrap_modes import vertical_prefix_from_module_import

def test_vertical_prefix_from_module_import_empty():
    # Test when imports is empty (lines 273-274)
    result = vertical_prefix_from_module_import(
        imports=[],
        statement="from module import ",
        comments=[],
        remove_comments=[],
        comment_prefix="#",
        line_length=80,
        line_separator="\n"
    )
    assert result == ""

def test_vertical_prefix_from_module_import_basic():
    # Test basic functionality without exceeding line length or triggering wrap
    result = vertical_prefix_from_module_import(
        imports=["a", "b"],
        statement="from module import ",
        comments=[],
        remove_comments=[],
        comment_prefix="#",
        line_length=80,
        line_separator="\n"
    )
    assert result == "from module import a, b"

def test_vertical_prefix_from_module_import_exceeds_line_length():
    # Test when adding next_import exceeds line length (lines 290-301)
    result = vertical_prefix_from_module_import(
        imports=["apple", "banana", "cherry"],
        statement="from module import ",
        comments=["# comment"],
        remove_comments=[],
        comment_prefix="#",
        line_length=25,
        line_separator="\n"
    )
    # This should trigger wrapping and execution of lines 271-308 including the wrap branch
    assert "apple" in result
    assert "banana" in result
    assert "cherry" in result

def test_vertical_prefix_from_module_import_comments_and_statement_with_comments():
    # Test the final `if comments and statement_with_comments:` condition (lines 306-307)
    result = vertical_prefix_from_module_import(
        imports=["a", "b"],
        statement="from module import ",
        comments=["# a comment"],
        remove_comments=[],
        comment_prefix="#",
        line_length=80,
        line_separator="\n"
    )
    assert "# a comment" in result
    assert "from module import a, b" in result
