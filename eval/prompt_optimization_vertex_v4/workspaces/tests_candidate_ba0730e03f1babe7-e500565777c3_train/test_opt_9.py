# file: src\sample_repo\isort\isort\wrap_modes.py:47-85
# asked: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}
# gained: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69]]}

import pytest
from isort.wrap_modes import grid


def test_grid_wrap_mode_comprehensive():
    # Test case 1: Empty imports list (returns "")
    res_empty = grid(imports=[])
    assert res_empty == ""

    # Test case 2: Basic grid wrapping without line length violation and without trailing comma
    # Executes: lines 49, 52, 53, 54, 55, 61 (False), 84, 85
    res_basic = grid(
        imports=["a", "b", "c"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
        white_space="    ",
        include_trailing_comma=False,
    )
    assert res_basic == "from module import (a, b, c)"

    # Test case 3: Line length violation branch triggering grid wrapping and splitting of next_import
    # We set line_length low so that adding next_import exceeds line_length,
    # and also test inner loop where `new_line` exceeds line_length (lines 68-71).
    # Specifically, next_import will be "verylongimportname part2" which when wrapped
    # will test both when line length is exceeded and when it is not (the `else` on line 71).
    res_wrap = grid(
        imports=["import1", "verylongimportname part2"],
        statement="from mod import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=15,
        white_space="    ",
        include_trailing_comma=True,
    )
    # Let's verify it contains the expected parts and properly executes lines 47-85.
    assert "import1" in res_wrap
    assert "verylongimportname" in res_wrap
    assert res_wrap.endswith(")")
