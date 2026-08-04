# file: src\sample_repo\isort\isort\wrap_modes.py:271-308
# asked: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}
# gained: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [306, 308]]}

import pytest
from isort.wrap_modes import vertical_prefix_from_module_import


def test_vertical_prefix_from_module_import_empty_imports():
    # Covers line 273-274: if not interface["imports"]: return ""
    result = vertical_prefix_from_module_import(
        imports=[],
        statement="from foo import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
    )
    assert result == ""


def test_vertical_prefix_from_module_import_single_import():
    # Covers single import (loop doesn't run, comments and statement_with_comments logic)
    result = vertical_prefix_from_module_import(
        imports=["bar"],
        statement="from foo import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
    )
    assert result == "from foo import bar"


def test_vertical_prefix_from_module_import_wrapping_and_comments():
    # Exercises lines 271-308 including the wrapping branch (line 290) and the final comments check (line 306)
    result = vertical_prefix_from_module_import(
        imports=["bar", "baz", "qux"],
        statement="from foo import ",
        comments=["# a comment"],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=20,  # forces line wrapping
    )
    assert isinstance(result, str)
    assert "from foo import" in result
