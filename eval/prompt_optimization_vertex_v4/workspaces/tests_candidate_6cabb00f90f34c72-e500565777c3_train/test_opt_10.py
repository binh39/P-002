# file: src\sample_repo\isort\isort\wrap_modes.py:47-85
# asked: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}
# gained: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}

from isort.wrap_modes import grid

def test_grid_wrap_mode_comprehensive():
    # Test case 1: empty imports (returns "")
    res_empty = grid(imports=[])
    assert res_empty == ""

    # Test case 2: imports without line length overflow and no trailing comma
    res_simple = grid(
        imports=["a", "b"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
        white_space="    ",
        include_trailing_comma=False,
    )
    assert res_simple == "from module import (a, b)"

    # Test case 3: imports with include_trailing_comma = True
    res_comma = grid(
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
    assert res_comma == "from module import (a, b,)"

    # Test case 4: triggering the line length overflow in grid mode (lines 61-82),
    # where next_import itself splits across multiple lines (lines 65-71).
    # We set line_length small so that combining statement and next_import exceeds line_length,
    # and also an import item with multiple words (e.g. "very_long_import_name as alias")
    # forces inner loop lines 66-71 to test both `len(new_line) + 1 > line_length` True and False branches.
    res_overflow = grid(
        imports=["a", "very_long_import_name_that_exceeds_length as alias"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=20,
        white_space="    ",
        include_trailing_comma=False,
    )
    assert "from module import (" in res_overflow
    assert "very_long_import_name_that_exceeds_length" in res_overflow
