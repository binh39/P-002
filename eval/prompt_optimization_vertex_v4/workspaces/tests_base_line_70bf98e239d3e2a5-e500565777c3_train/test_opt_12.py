# file: src\sample_repo\isort\isort\wrap_modes.py:47-85
# asked: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}
# gained: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69]]}

from isort.wrap_modes import grid

def test_grid_wrap_mode_execution():
    # 1. Test empty imports (covers line 49-50)
    res_empty = grid(
        imports=[],
        statement="from module import",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_length=80,
        line_separator="\n",
        white_space="    ",
        include_trailing_comma=False,
    )
    assert res_empty == ""

    # 2. Test grid normal flow where next_statement fits within line_length (covers `else` branch at line 83-84)
    res_fits = grid(
        imports=["a", "b"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_length=80,
        line_separator="\n",
        white_space="    ",
        include_trailing_comma=True,
    )
    assert res_fits == "from module import (a, b,)"

    # 3. Test grid wrap mode when next_statement exceeds line_length (covers lines 61-82)
    # Also inside the `if`:
    # - inner loop over parts of `next_import` (lines 66-71)
    # - where `new_line` exceeds line_length (covers `if len(new_line) + 1 > interface["line_length"]:` line 68)
    # - and where it doesn't (covers `else:` line 70-71)
    res_exceeds = grid(
        imports=["short", "very_long_import_part1 very_long_import_part2"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_length=20,
        line_separator="\n",
        white_space="    ",
        include_trailing_comma=False,
    )
    assert "very_long_import_part1" in res_exceeds
    assert "very_long_import_part2" in res_exceeds
