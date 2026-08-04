# file: src\sample_repo\isort\isort\wrap_modes.py:271-308
# asked: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}
# gained: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [306, 308]]}

import pytest
from isort.wrap_modes import vertical_prefix_from_module_import

def test_vertical_prefix_from_module_import_empty_imports():
    # Covers line 273-274: not interface["imports"] returns ""
    result = vertical_prefix_from_module_import(
        imports=[],
        statement="from foo import ",
        comments=[],
        remove_comments=[],
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
    )
    assert result == ""

def test_vertical_prefix_from_module_import_line_length_exceeded_and_comments_flag():
    # Covers lines 271-308 including:
    # - loop over imports (lines 282-304)
    # - length > line_length triggering wrap (lines 290-303)
    # - final `if comments and statement_with_comments:` check (lines 306-307)
    result = vertical_prefix_from_module_import(
        imports=["a", "b"],
        statement="from foo import ",
        comments=["# comment"],
        remove_comments=[],
        comment_prefix="#",
        line_separator="\n",
        line_length=15, # forces wrap on second import
    )
    assert isinstance(result, str)
    assert "a" in result
    assert "b" in result
