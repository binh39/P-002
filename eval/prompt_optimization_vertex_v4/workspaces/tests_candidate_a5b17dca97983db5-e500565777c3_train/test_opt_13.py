# file: src\sample_repo\isort\isort\wrap_modes.py:47-85
# asked: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}
# gained: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69]]}

from isort.wrap_modes import grid

def test_grid_wrap_mode_empty_imports():
    res = grid(
        imports=[],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_length=80,
        line_separator="\n",
        white_space="    ",
        include_trailing_comma=False,
    )
    assert res == ""

def test_grid_wrap_mode_basic_no_exceed():
    res = grid(
        imports=["a", "b"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_length=80,
        line_separator="\n",
        white_space="    ",
        include_trailing_comma=False,
    )
    assert res == "from module import (a, b)"

def test_grid_wrap_mode_exceed_line_length_single_import_parts():
    res = grid(
        imports=["a", "very_long_import_name_that_exceeds_line_length_limit"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_length=30,
        line_separator="\n",
        white_space="    ",
        include_trailing_comma=True,
    )
    assert "(" in res
    assert res.endswith(")")

def test_grid_wrap_mode_long_import_multiple_parts():
    # Tests the loop over next_import.split(" ")[1:] with both the if and else inside it (wrapping vs appending)
    res = grid(
        imports=["a", "part1 part2_very_long_part_to_force_wrap"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_length=20,
        line_separator="\n",
        white_space="    ",
        include_trailing_comma=False,
    )
    assert "(" in res
    assert res.endswith(")")
