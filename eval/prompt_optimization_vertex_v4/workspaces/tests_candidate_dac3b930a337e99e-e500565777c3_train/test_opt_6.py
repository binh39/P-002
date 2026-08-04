# file: src\sample_repo\isort\isort\wrap_modes.py:117-167
# asked: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}
# gained: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [146, 147], [146, 167], [153, 156], [153, 157]]}

import pytest
from isort.wrap_modes import hanging_indent


def test_hanging_indent_empty_imports():
    """Test hanging_indent when imports list is empty (line 119-120)."""
    result = hanging_indent(
        imports=[],
        statement="import ",
        line_length=80,
        line_separator="\n",
        indent="    ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
    )
    assert result == ""


def test_hanging_indent_first_import_exceeds_limit():
    """Test hanging_indent when first import makes statement exceed line length limit (line 127-132)."""
    result = hanging_indent(
        imports=["very_long_import_name"],
        statement="import ",
        line_length=20,
        line_separator="\n",
        indent="    ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
    )
    assert "\\" in result
    assert "very_long_import_name" in result


def test_hanging_indent_multiple_imports_and_wrapping():
    """Test hanging_indent with multiple imports where subsequent ones trigger wrapping (line 136-144)."""
    result = hanging_indent(
        imports=["a", "b" * 30],
        statement="from mod import ",
        line_length=25,
        line_separator="\n",
        indent="    ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
    )
    assert result is not None
    assert "\n    " in result


def test_hanging_indent_with_comments_short_enough():
    """Test hanging_indent with comments where statement_with_comments fits within limit (lines 146-156)."""
    result = hanging_indent(
        imports=["a"],
        statement="import ",
        line_length=80,
        line_separator="\n",
        indent="    ",
        comments=["comment"],
        remove_comments=False,
        comment_prefix="#",
    )
    assert "comment" in result


def test_hanging_indent_with_comments_too_long():
    """Test hanging_indent with comments where statement_with_comments exceeds limit, wrapping comment (lines 157-164)."""
    result = hanging_indent(
        imports=["a"],
        statement="import ",
        line_length=15,
        line_separator="\n",
        indent="    ",
        comments=["very_long_comment_here"],
        remove_comments=False,
        comment_prefix="#",
    )
    assert result is not None
    assert "\n" in result
