# file: src\sample_repo\isort\isort\wrap_modes.py:271-308
# asked: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}
# gained: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}

import pytest
from isort.wrap_modes import vertical_prefix_from_module_import

def test_vertical_prefix_from_module_import_empty():
    # Test when imports list is empty (lines 273-274)
    result = vertical_prefix_from_module_import(
        statement="from module import ",
        imports=[],
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
    )
    assert result == ""

def test_vertical_prefix_from_module_import_basic():
    # Test basic wrapping without exceeding line length and no comments at the end
    result = vertical_prefix_from_module_import(
        statement="from module import ",
        imports=["a", "b"],
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
    )
    assert result == "from module import a, b"

def test_vertical_prefix_from_module_import_exceeds_length():
    # Test when line length is exceeded, triggering lines 291-301
    result = vertical_prefix_from_module_import(
        statement="from module import ",
        imports=["apple", "banana", "cherry"],
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=25,
    )
    # Expected behavior should wrap when line length exceeds 25
    assert "\n" in result

def test_vertical_prefix_from_module_import_with_comments():
    # Test when comments and statement_with_comments are present at the end (lines 306-307)
    result = vertical_prefix_from_module_import(
        statement="from module import ",
        imports=["a", "b"],
        comments=["# comment"],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
    )
    assert "from module import a, b" in result
    assert "# comment" in result
