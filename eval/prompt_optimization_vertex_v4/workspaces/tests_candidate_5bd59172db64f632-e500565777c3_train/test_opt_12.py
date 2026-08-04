# file: src\sample_repo\isort\isort\wrap_modes.py:47-85
# asked: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}
# gained: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}

import pytest
from isort.wrap_modes import grid

def test_grid_wrap_mode_comprehensive():
    # 1. Test empty imports -> returns ""
    res_empty = grid(
        imports=[],
        statement="from module import",
        line_length=80,
        line_separator="\n",
        white_space="    ",
        remove_comments=False,
        comment_prefix="#",
        comments={},
        include_trailing_comma=False,
    )
    assert res_empty == ""

    # 2. Test standard grid without exceeding line length (hits else branch at line 84, include_trailing_comma=True)
    res_normal = grid(
        imports=["a", "b", "c"],
        statement="from module import ",
        line_length=80,
        line_separator="\n",
        white_space="    ",
        remove_comments=False,
        comment_prefix="#",
        comments={},
        include_trailing_comma=True,
    )
    assert res_normal == "from module import (a, b, c,)"

    # 3. Test grid with a next_import exceeding line length (triggers lines 61-82),
    # and inside that, multi-word import parts where some lines wrap and some don't (lines 66-71).
    res_long = grid(
        imports=["alpha", "beta gamma delta epsilon zeta eta theta iota kappa"],
        statement="from module import ",
        line_length=20,
        line_separator="\n",
        white_space="    ",
        remove_comments=False,
        comment_prefix="#",
        comments={},
        include_trailing_comma=False,
    )
    # Let's verify it executes successfully and returns a string with parentheses.
    assert res_long.startswith("from module import (alpha")
    assert res_long.endswith(")")
