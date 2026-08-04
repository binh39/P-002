# file: src\sample_repo\isort\isort\wrap_modes.py:47-85
# asked: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}
# gained: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69]]}

from isort.wrap_modes import grid

def test_grid_wrap_mode_comprehensive():
    # Test case 1: empty imports (returns "")
    res_empty = grid(imports=[])
    assert res_empty == ""

    # Test case 2: imports without line length overflow (hits line 84: else branch)
    # Also test include_trailing_comma=True and False
    res_no_overflow_no_comma = grid(
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
    assert res_no_overflow_no_comma == "from module import (a, b)"

    res_no_overflow_with_comma = grid(
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
    assert res_no_overflow_with_comma == "from module import (a, b,)"

    # Test case 3: imports with line length overflow triggering the `if` block (lines 61-82)
    # Within this block, test:
    # - next_import containing multiple parts separated by spaces (lines 66-71: parts loop with line_length check true/false)
    res_overflow = grid(
        imports=["a", "very_long_import_name_that_forces_wrapping with_subparts"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=20,  # very short line length to force overflow
        white_space="    ",
        include_trailing_comma=True,
    )
    assert "from module import" in res_overflow
    assert "very_long_import_name_that_forces_wrapping" in res_overflow
    assert res_overflow.endswith(")")
