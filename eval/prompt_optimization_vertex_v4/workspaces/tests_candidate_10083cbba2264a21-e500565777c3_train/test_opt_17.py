# file: src\sample_repo\isort\isort\wrap_modes.py:271-308
# asked: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}
# gained: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}

import pytest
from isort.wrap_modes import vertical_prefix_from_module_import

def test_vertical_prefix_from_module_import_empty_imports():
    # Covers line 273-274
    result = vertical_prefix_from_module_import(
        imports=[],
        statement="from module import ",
        comments=[],
        remove_comments=set(),
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
    )
    assert result == ""

def test_vertical_prefix_from_module_import_normal():
    # Covers lines 276-288, 306-308 without triggering line length wrap or condition in 306
    result = vertical_prefix_from_module_import(
        imports=["a", "b"],
        statement="from module import ",
        comments=[],
        remove_comments=set(),
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
    )
    assert result == "from module import a, b"

def test_vertical_prefix_from_module_import_line_length_exceeded():
    # Triggers the wrap condition (lines 291-303)
    result = vertical_prefix_from_module_import(
        imports=["very_long_import_name_one", "very_long_import_name_two"],
        statement="from module import ",
        comments=["# comment"],
        remove_comments=set(),
        comment_prefix="#",
        line_separator="\n",
        line_length=30,
    )
    assert "very_long_import_name_one" in result
    assert "very_long_import_name_two" in result

def test_vertical_prefix_from_module_import_comments_and_statement_with_comments():
    # Triggers the condition `if comments and statement_with_comments:` on lines 306-307
    result = vertical_prefix_from_module_import(
        imports=["a", "b"],
        statement="from module import ",
        comments=["# comment"],
        remove_comments=set(),
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
    )
    assert "from module import a, b" in result
    assert "# comment" in result
