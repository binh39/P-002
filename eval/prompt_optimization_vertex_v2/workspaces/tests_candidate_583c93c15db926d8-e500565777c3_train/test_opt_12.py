# file: src\sample_repo\isort\isort\wrap_modes.py:271-308
# asked: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}
# gained: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}

import pytest
from isort.wrap_modes import vertical_prefix_from_module_import

def test_vertical_prefix_from_module_import_empty_imports():
    # Covers line 273: if not interface["imports"]: return ""
    result = vertical_prefix_from_module_import(
        imports=[],
        statement="from foo import ",
        comments=[],
        remove_comments=[],
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
    )
    assert result == ""

def test_vertical_prefix_from_module_import_no_line_wrap():
    # Covers normal execution loop without exceeding line length,
    # and tests the final return.
    result = vertical_prefix_from_module_import(
        imports=["a", "b"],
        statement="from foo import ",
        comments=[],
        remove_comments=[],
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
    )
    assert result == "from foo import a, b"

def test_vertical_prefix_from_module_import_exceeds_line_length():
    # Covers branch where line length is exceeded inside the loop (lines 290-303).
    result = vertical_prefix_from_module_import(
        imports=["apple", "banana"],
        statement="from fruit import ",
        comments=[],
        remove_comments=[],
        comment_prefix="#",
        line_separator="\n",
        line_length=20,  # small enough to force wrap on second import
    )
    # With line_length=20:
    # output_statement = "from fruit import apple" (len 23, but first)
    # next: "banana" -> statement = "from fruit import apple, banana"
    # exceeds line length, triggers wrap branch.
    assert "apple" in result
    assert "banana" in result
    assert "\n" in result

def test_vertical_prefix_from_module_import_with_comments_and_statement_with_comments():
    # Covers lines 306-307: if comments and statement_with_comments: output_statement = statement_with_comments
    result = vertical_prefix_from_module_import(
        imports=["a", "b"],
        statement="from foo import ",
        comments=["# comment"],
        remove_comments=[],
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
    )
    assert "a, b" in result
