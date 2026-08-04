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
        line_length=80,
        line_separator="\n",
    )
    assert result == ""


def test_vertical_prefix_from_module_import_normal():
    # Covers lines 271-308 without triggering the wrap condition or the final comments condition
    result = vertical_prefix_from_module_import(
        imports=["a", "b"],
        statement="from module import ",
        comments=[],
        remove_comments=[],
        comment_prefix="#",
        line_length=80,
        line_separator="\n",
    )
    assert result == "from module import a, b"


def test_vertical_prefix_from_module_import_exceeds_line_length():
    # Covers lines 290-301 (line length exceeded branch)
    result = vertical_prefix_from_module_import(
        imports=["very_long_import_name_a", "very_long_import_name_b"],
        statement="from module import ",
        comments=[],
        remove_comments=[],
        comment_prefix="#",
        line_length=25,
        line_separator="\n",
    )
    assert "very_long_import_name_a" in result
    assert "very_long_import_name_b" in result


def test_vertical_prefix_from_module_import_with_comments():
    # Covers lines 306-307 (if comments and statement_with_comments:)
    # With multiple imports so the loop runs and statement_with_comments gets populated.
    result = vertical_prefix_from_module_import(
        imports=["a", "b"],
        statement="from module import ",
        comments=["# comment"],
        remove_comments=[],
        comment_prefix="#",
        line_length=80,
        line_separator="\n",
    )
    assert "# comment" in result
