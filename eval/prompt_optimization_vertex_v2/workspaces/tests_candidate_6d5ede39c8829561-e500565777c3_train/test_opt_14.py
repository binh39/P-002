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
        remove_comments=False,
        comment_prefix="#",
        line_length=80,
        line_separator="\n",
    )
    assert result == ""

def test_vertical_prefix_from_module_import_single_import():
    # Covers single import (loop doesn't run)
    result = vertical_prefix_from_module_import(
        imports=["bar"],
        statement="from foo import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_length=80,
        line_separator="\n",
    )
    assert result == "from foo import bar"

def test_vertical_prefix_from_module_import_exceeds_line_length():
    # Covers line 291-301: line length exceeded inside the loop, triggering wrap logic
    result = vertical_prefix_from_module_import(
        imports=["bar", "baz"],
        statement="from foo import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_length=20,  # Small line length to force wrap
        line_separator="\n",
    )
    # With statement="from foo import ", first import "bar" -> "from foo import bar" (len 16)
    # Next import "baz" -> statement becomes "from foo import bar, baz" (len 21 > 20)
    # This triggers the wrap branch.
    assert result is not None
    assert isinstance(result, str)
    assert "bar" in result
    assert "baz" in result

def test_vertical_prefix_from_module_import_with_comments_and_statement_with_comments():
    # Covers lines 306-307: if comments and statement_with_comments: output_statement = statement_with_comments
    result = vertical_prefix_from_module_import(
        imports=["bar", "baz"],
        statement="from foo import ",
        comments=["# comment"],
        remove_comments=False,
        comment_prefix="#",
        line_length=80,
        line_separator="\n",
    )
    assert result is not None
    assert isinstance(result, str)
    assert "bar" in result
    assert "baz" in result
