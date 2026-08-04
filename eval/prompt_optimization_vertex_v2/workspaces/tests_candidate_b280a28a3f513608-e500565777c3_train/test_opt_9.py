# file: src\sample_repo\isort\isort\wrap_modes.py:47-85
# asked: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}
# gained: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 84]]}

from isort.wrap_modes import grid

def test_grid_wrap_mode_execution():
    # Test empty imports (lines 49-50)
    res_empty = grid(
        imports=[],
        statement="from module import",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
        white_space="    ",
        include_trailing_comma=False,
    )
    assert res_empty == ""

    # Test basic grid wrap with multiple imports fitting on one line (lines 52-59, 84-85)
    res_normal = grid(
        imports=["a", "b"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
        white_space="    ",
        include_trailing_comma=True,
    )
    assert res_normal == "from module import (a, b,)"

    # Test grid wrap where next_import exceeds line length (lines 61-82)
    # Also tests when parts of next_import exceed line length (lines 65-72)
    res_long = grid(
        imports=["very_long_import_name_that_exceeds_line_length_completely_on_its_own as v"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=30,
        white_space="    ",
        include_trailing_comma=False,
    )
    # Should trigger wrapping inside the import parts as well
    assert "very_long_import_name_that_exceeds_line_length_completely_on_its_own" in res_long
    assert res_long.endswith(")")
