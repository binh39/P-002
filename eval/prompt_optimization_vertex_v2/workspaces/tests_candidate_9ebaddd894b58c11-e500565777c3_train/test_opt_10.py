# file: src\sample_repo\isort\isort\wrap_modes.py:271-308
# asked: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}
# gained: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 308]]}

import pytest
from isort.wrap_modes import vertical_prefix_from_module_import

def test_vertical_prefix_from_module_import_empty():
    # Covers line 273 (not interface["imports"])
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

def test_vertical_prefix_from_module_import_basic():
    # Covers normal execution without exceeding line length, and tests line 306 branch where comments/statement_with_comments might be falsy
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

def test_vertical_prefix_from_module_import_wrap_and_comments():
    # Covers:
    # - Line 282 loop with multiple imports
    # - Line 291 line length exceeded branch (wrapping happens)
    # - Line 306 (`if comments and statement_with_comments:`)
    result = vertical_prefix_from_module_import(
        imports=["very_long_import_name_one", "very_long_import_name_two"],
        statement="from module import ",
        comments=["# a comment"],
        remove_comments=set(),
        comment_prefix="#",
        line_separator="\n",
        line_length=30,
    )
    assert "very_long_import_name_one" in result
    assert "very_long_import_name_two" in result
