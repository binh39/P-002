# file: src\sample_repo\isort\isort\wrap_modes.py:271-308
# asked: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}
# gained: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 308]]}

from isort.wrap_modes import vertical_prefix_from_module_import

def test_vertical_prefix_from_module_import_empty():
    # Covers line 273 (no imports)
    result = vertical_prefix_from_module_import(
        imports=[],
        statement="from mod import ",
        comments=[],
        remove_comments=[],
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
    )
    assert result == ""


def test_vertical_prefix_from_module_import_basic():
    # Covers lines 271-308 with a simple single/multiple import case without wrapping or trailing comments condition
    result = vertical_prefix_from_module_import(
        imports=["a", "b"],
        statement="from mod import ",
        comments=[],
        remove_comments=[],
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
    )
    assert result == "from mod import a, b"


def test_vertical_prefix_from_module_import_wrap_and_comments():
    # Covers wrapping logic (lines 290-303) and final `if comments and statement_with_comments:` (lines 306-307)
    result = vertical_prefix_from_module_import(
        imports=["very_long_import_name_one", "very_long_import_name_two"],
        statement="from mod import ",
        comments=["# a comment"],
        remove_comments=[],
        comment_prefix="#",
        line_separator="\n",
        line_length=20,  # Force wrap immediately
    )
    assert "very_long_import_name_one" in result
    assert "very_long_import_name_two" in result
