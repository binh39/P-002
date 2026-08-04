# file: src\sample_repo\isort\isort\wrap_modes.py:47-85
# asked: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}
# gained: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}

from isort.wrap_modes import grid

def test_grid_empty_imports():
    result = grid(imports=[])
    assert result == ""

def test_grid_no_wrap():
    # Covers:
    # - non-empty imports
    # - loop executing where `len(next_statement.split(...) ...)` <= line_length (else branch: line 84)
    # - include_trailing_comma = True and False
    result = grid(
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
    assert result == "from module import (a, b,)"

    result_no_comma = grid(
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
    assert result_no_comma == "from module import (a, b)"

def test_grid_wrap_and_sub_wrap():
    # Covers:
    # - line 61/62: `len(next_statement.split(...) ...)` > line_length (triggers inner wrapping logic lines 65-82)
    # - inner loop over split parts of next_import (lines 66-71)
    # - inner loop where `len(new_line) + 1 > interface["line_length"]` is True (line 68) and False (line 70)
    # - comments resetting (`interface["comments"] = []`)
    result = grid(
        imports=["a", "very_long_import_name_that_forces_wrapping as alias"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=30,
        white_space="    ",
        include_trailing_comma=True,
    )
    assert "very_long_import_name_that_forces_wrapping" in result
    assert result.endswith(")")
