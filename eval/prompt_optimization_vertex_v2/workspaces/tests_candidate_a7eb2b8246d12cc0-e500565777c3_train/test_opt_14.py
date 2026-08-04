# file: src\sample_repo\isort\isort\wrap_modes.py:271-308
# asked: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}
# gained: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}

import pytest
from isort.wrap_modes import vertical_prefix_from_module_import

def test_vertical_prefix_from_module_import_empty():
    # Covers: if not interface["imports"]: return ""
    res = vertical_prefix_from_module_import(
        imports=[],
        statement="from a import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
    )
    assert res == ""

def test_vertical_prefix_from_module_import_no_wrap():
    # Covers normal loop execution without line length overflow, and false branch for `if comments and statement_with_comments:`
    res = vertical_prefix_from_module_import(
        imports=["b", "c"],
        statement="from a import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
    )
    assert res == "from a import b, c"

def test_vertical_prefix_from_module_import_wrap_triggered():
    # Covers line length overflow branch inside the loop:
    # len(statement_with_comments.split(line_separator)[-1]) + 1 > line_length
    res = vertical_prefix_from_module_import(
        imports=["very_long_import_name_one", "very_long_import_name_two"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=25,
    )
    assert "very_long_import_name_one" in res
    assert "very_long_import_name_two" in res

def test_vertical_prefix_from_module_import_comments_and_statement_with_comments():
    # Covers: if comments and statement_with_comments: output_statement = statement_with_comments
    res = vertical_prefix_from_module_import(
        imports=["b", "c"],
        statement="from a import ",
        comments=["# comment"],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
    )
    assert "from a import b, c" in res
    assert "# comment" in res
