# file: src\sample_repo\isort\isort\wrap_modes.py:117-167
# asked: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}
# gained: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}

import pytest
from isort.wrap_modes import hanging_indent, formatter_from_string

def test_hanging_indent_empty_imports():
    # Covers line 119-120: if not interface["imports"]: return ""
    result = hanging_indent(
        statement="import a",
        imports=[],
        white_space=" ",
        indent="    ",
        line_length=80,
        comments=[],
        line_separator="\n",
        comment_prefix="#",
        include_trailing_comma=False,
        remove_comments=False,
    )
    assert result == ""

def test_hanging_indent_first_import_too_long():
    # Covers line 127-132: len(next_statement) > line_length_limit for first import
    # line_length = 15 -> line_length_limit = 12
    # statement="import ", next_import="very_long_import_name" -> len > 12
    result = hanging_indent(
        statement="import ",
        imports=["very_long_import_name"],
        white_space=" ",
        indent="    ",
        line_length=15,
        comments=[],
        line_separator="\n",
        comment_prefix="#",
        include_trailing_comma=False,
        remove_comments=False,
    )
    assert "\\" in result
    assert "very_long_import_name" in result

def test_hanging_indent_subsequent_import_too_long():
    # Covers line 139-142: len(next_statement.split(interface["line_separator"])[-1]) > line_length_limit in while loop
    # line_length = 20 -> line_length_limit = 17
    result = hanging_indent(
        statement="import ",
        imports=["short", "this_is_a_very_long_subsequent_import_to_trigger_wrap"],
        white_space=" ",
        indent="    ",
        line_length=20,
        comments=[],
        line_separator="\n",
        comment_prefix="#",
        include_trailing_comma=False,
        remove_comments=False,
    )
    assert "\\" in result
    assert "this_is_a_very_long_subsequent_import_to_trigger_wrap" in result

def test_hanging_indent_with_comments_short_line():
    # Covers lines 146-156: comments present and statement_with_comments fits within line_length_limit + 2
    # line_length = 40 -> line_length_limit = 37, limit+2 = 39
    result = hanging_indent(
        statement="import a",
        imports=["b"],
        white_space=" ",
        indent="    ",
        line_length=50,
        comments=["# comment"],
        line_separator="\n",
        comment_prefix="#",
        include_trailing_comma=False,
        remove_comments=False,
    )
    assert "# comment" in result

def test_hanging_indent_with_comments_long_line():
    # Covers lines 157-164: comments present and statement_with_comments exceeds line_length_limit + 2
    # Forces splitting comment to next line with indent
    result = hanging_indent(
        statement="import ",
        imports=["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"],
        white_space=" ",
        indent="    ",
        line_length=15,
        comments=["# a very long comment that will exceed limits"],
        line_separator="\n",
        comment_prefix="#",
        include_trailing_comma=False,
        remove_comments=False,
    )
    assert "\n" in result
    assert "# a very long comment that will exceed limits" in result

def test_hanging_indent_no_comments_returns_statement():
    # Covers line 167: return str(interface["statement"]) when no comments are present
    # Note: imports must be non-empty so that it doesn't return "" at line 120,
    # and processes the statement properly without comments.
    result = hanging_indent(
        statement="import ",
        imports=["a"],
        white_space=" ",
        indent="    ",
        line_length=80,
        comments=[],
        line_separator="\n",
        comment_prefix="#",
        include_trailing_comma=False,
        remove_comments=False,
    )
    assert result == "import a"

def test_formatter_from_string_hanging_indent():
    formatter = formatter_from_string("HANGING_INDENT")
    assert callable(formatter)
