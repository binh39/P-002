# file: src\sample_repo\isort\isort\wrap_modes.py:271-308
# asked: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}
# gained: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 308]]}

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
        line_length=80,
        line_separator="\n"
    )
    assert result == ""

def test_vertical_prefix_from_module_import_no_wrap():
    # Covers basic execution with imports, without exceeding line length
    imports = ["a", "b", "c"]
    result = vertical_prefix_from_module_import(
        imports=imports,
        statement="from foo import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_length=80,
        line_separator="\n"
    )
    assert result == "from foo import a, b, c"

def test_vertical_prefix_from_module_import_exceeds_line_length():
    # Covers lines 290-303 (wrap triggered) and lines 306-307 (comments and statement_with_comments truthy)
    imports = ["long_import_name_one", "long_import_name_two"]
    result = vertical_prefix_from_module_import(
        imports=imports,
        statement="from foo import ",
        comments=["# comment"],
        remove_comments=False,
        comment_prefix="#",
        line_length=25,  # small enough to trigger wrap on second import
        line_separator="\n"
    )
    assert "long_import_name_one" in result
    assert "long_import_name_two" in result
