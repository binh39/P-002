# file: src\sample_repo\isort\isort\wrap_modes.py:47-85
# asked: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}
# gained: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69]]}

import pytest
from isort.wrap_modes import grid


def test_grid_wrap_mode_comprehensive():
    # Test case 1: Empty imports list (returns "")
    res_empty = grid(imports=[])
    assert res_empty == ""

    # Test case 2: Basic grid wrapping without line length violation (enters else branch at line 84)
    res_basic = grid(
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
    assert res_basic == "from module import (a, b)"

    # Test case 3: Include trailing comma enabled
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

    # Test case 4: Line length exceeded, triggering the `if` branch at line 61,
    # with inner `if len(new_line) + 1 > interface['line_length']` triggered and untriggered (else branch at line 71).
    # Also tests multi-word imports ("word1 word2 word3") and comments handling.
    res_long = grid(
        imports=["a", "long_import_word1 word2 word_super_long_part3"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=20,
        white_space="    ",
        include_trailing_comma=True,
    )
    # This should exercise:
    # - lines 53-54 (while loop)
    # - lines 55-59 (add_to_line)
    # - line 61 (line length check > line_length -> True)
    # - lines 65-72 (splitting long import into multiple parts, testing line 68 `if` and line 71 `else`)
    # - lines 73-82 (statement update, adding comments, resetting comments=[])
    # - line 85 (trailing comma handling and closing parenthesis)
    assert "(" in res_long
    assert ")" in res_long
    assert res_long.endswith(")")
