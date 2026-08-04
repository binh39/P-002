# file: src\sample_repo\isort\isort\wrap_modes.py:271-308
# asked: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}
# gained: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}

import pytest
from isort.wrap_modes import vertical_prefix_from_module_import

def test_vertical_prefix_from_module_import_empty_imports():
    # Covers: if not interface["imports"]: return ""
    result = vertical_prefix_from_module_import(
        imports=[],
        statement="from module import ",
        comments=[],
        remove_comments=set(),
        comment_prefix="#",
        line_length=80,
        line_separator="\n",
    )
    assert result == ""

def test_vertical_prefix_from_module_import_no_wrap():
    # Covers normal loop execution without line_length being exceeded,
    # and tests the final `if comments and statement_with_comments:` branches (false/true).
    # With comments and statement_with_comments set:
    result = vertical_prefix_from_module_import(
        imports=["a", "b"],
        statement="from module import ",
        comments=["# comment"],
        remove_comments=set(),
        comment_prefix="#",
        line_length=80,
        line_separator="\n",
    )
    assert "a" in result
    assert "b" in result

def test_vertical_prefix_from_module_import_wrap_triggered():
    # Triggers line length limit inside the loop (lines 290-303)
    # and exercises `if comments and statement_with_comments:` condition.
    result = vertical_prefix_from_module_import(
        imports=["very_long_import_name_one", "very_long_import_name_two"],
        statement="from module import ",
        comments=["# comment"],
        remove_comments=set(),
        comment_prefix="#",
        line_length=20,
        line_separator="\n",
    )
    assert "very_long_import_name_one" in result
    assert "very_long_import_name_two" in result

def test_vertical_prefix_no_comments_with_statement_with_comments():
    # Tests `if comments and statement_with_comments:` when comments is empty / falsy.
    result = vertical_prefix_from_module_import(
        imports=["a", "b"],
        statement="from module import ",
        comments=[],
        remove_comments=set(),
        comment_prefix="#",
        line_length=80,
        line_separator="\n",
    )
    assert "a" in result
    assert "b" in result
