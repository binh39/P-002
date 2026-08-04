# file: src\sample_repo\isort\isort\wrap_modes.py:186-219
# asked: {"lines": [186, 187, 188, 190, 191, 192, 193, 194, 195, 197, 198, 199, 201, 202, 203, 204, 205, 207, 208, 210, 211, 212, 213, 214, 216, 217, 218, 219], "branches": [[187, 188], [187, 190], [201, 202], [201, 217], [205, 207], [205, 208], [208, 210], [208, 211], [211, 212], [211, 216], [217, 218], [217, 219]]}
# gained: {"lines": [186, 187, 188, 190, 191, 192, 193, 194, 195, 197, 198, 199, 201, 202, 203, 204, 205, 207, 208, 210, 211, 212, 213, 214, 216, 217, 218, 219], "branches": [[187, 188], [187, 190], [201, 202], [201, 217], [205, 207], [208, 210], [211, 212], [217, 218]]}

import pytest
from isort.wrap_modes import _vertical_grid_common

def test_vertical_grid_common_basic():
    # Test empty imports (line 187-188)
    res = _vertical_grid_common(
        True,
        imports=[],
        statement="from module import",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        indent="    ",
        line_length=80,
        include_trailing_comma=False,
    )
    assert res == ""

def test_vertical_grid_common_single_and_multiple_imports():
    # Test non-empty imports, wrapping, trailing comma, and line length overflow
    res = _vertical_grid_common(
        need_trailing_char=True,
        imports=["a", "b_very_long_import_name_to_trigger_wrap"],
        statement="from module import",
        comments=["# comment"],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        indent="    ",
        line_length=20,
        include_trailing_comma=True,
    )
    # This should exercise:
    # - adding comments
    # - loop over imports (lines 201-216)
    # - current_line_length calculation with imports remaining or trailing comma (lines 205-207)
    # - current_line_length with no imports remaining and need_trailing_char (lines 208-210)
    # - line length exceeding line_length causing wrapping (lines 211-214)
    # - include_trailing_comma adding a comma at the end (lines 217-218)
    assert isinstance(res, str)
    assert "a" in res
    assert "b_very_long_import_name_to_trigger_wrap" in res
