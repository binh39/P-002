# file: src\sample_repo\isort\isort\wrap_modes.py:271-308
# asked: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}
# gained: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 308]]}

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
    result = vertical_prefix_from_module_import(
        imports=["a", "b"],
        statement="from my_module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_length=80,
        line_separator="\n",
    )
    assert "a" in result
    assert "b" in result

def test_vertical_prefix_from_module_import_wrap_and_comments():
    # This test exercises lines 271-308 including the wrapping branch (line 290)
    # and the final conditional (line 306).
    result = vertical_prefix_from_module_import(
        imports=["apple", "banana", "cherry"],
        statement="from my_module import ",
        comments=["# a comment"],
        remove_comments=False,
        comment_prefix="#",
        line_length=25,  # force wrap early
        line_separator="\n",
    )
    assert isinstance(result, str)
    assert "apple" in result
    assert "banana" in result
    assert "cherry" in result
