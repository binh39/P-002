# file: src\sample_repo\isort\isort\wrap_modes.py:271-308
# asked: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}
# gained: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}

import pytest
from isort.wrap_modes import vertical_prefix_from_module_import

def test_vertical_prefix_from_module_import_empty():
    # Covers line 273 (not interface["imports"])
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
    # Covers general execution without line length overflow and without final comments/statement_with_comments
    imports = ["a", "b"]
    result = vertical_prefix_from_module_import(
        imports=imports,
        statement="from module import ",
        comments=[],
        remove_comments=[],
        comment_prefix="#",
        line_length=80,
        line_separator="\n",
    )
    assert result == "from module import a, b"

def test_vertical_prefix_from_module_import_line_length_overflow():
    # Triggers line_length overflow condition (lines 290-303)
    imports = ["long_import_name_one", "long_import_name_two"]
    result = vertical_prefix_from_module_import(
        imports=list(imports),
        statement="from module import ",
        comments=[],
        remove_comments=[],
        comment_prefix="#",
        line_length=25,
        line_separator="\n",
    )
    assert "long_import_name_one" in result
    assert "long_import_name_two" in result
    assert "\n" in result

def test_vertical_prefix_from_module_import_with_comments():
    # Triggers lines 306-307 (if comments and statement_with_comments)
    imports = ["a", "b"]
    result = vertical_prefix_from_module_import(
        imports=list(imports),
        statement="from module import ",
        comments=["a comment"],
        remove_comments=False,
        comment_prefix="#",
        line_length=80,
        line_separator="\n",
    )
    assert result == "from module import a, b# a comment"
