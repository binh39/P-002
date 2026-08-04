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
        remove_comments=[],
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
    )
    assert result == ""


def test_vertical_prefix_from_module_import_no_wrap_no_comments():
    # Covers: basic loop without wrapping, comments/statement_with_comments empty at end
    result = vertical_prefix_from_module_import(
        imports=["a", "b"],
        statement="from module import ",
        comments=[],
        remove_comments=[],
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
    )
    assert result == "from module import a, b"


def test_vertical_prefix_from_module_import_with_wrap():
    # Covers: line length exceeded branch triggering wrap (lines 290-303)
    result = vertical_prefix_from_module_import(
        imports=["very_long_import_name_one", "very_long_import_name_two"],
        statement="from module import ",
        comments=["# comment"],
        remove_comments=[],
        comment_prefix="#",
        line_separator="\n",
        line_length=30,
    )
    assert "very_long_import_name_one" in result
    assert "very_long_import_name_two" in result


def test_vertical_prefix_from_module_import_comments_and_statement_with_comments():
    # Covers: if comments and statement_with_comments: output_statement = statement_with_comments (lines 306-307)
    # Note: imports must have at least 2 items so that the loop over interface["imports"] runs at least once,
    # populating statement_with_comments while comments remains non-empty.
    result = vertical_prefix_from_module_import(
        imports=["a", "b"],
        statement="from module import ",
        comments=["# a comment"],
        remove_comments=[],
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
    )
    assert "# a comment" in result
