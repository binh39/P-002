# file: src\sample_repo\isort\isort\wrap_modes.py:47-85
# asked: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}
# gained: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69]]}

import pytest
from isort.wrap_modes import grid

def test_grid_empty_imports():
    res = grid(
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
    assert res == ""

def test_grid_simple_wrap():
    res = grid(
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
    assert res == "from module import (a, b,)"

def test_grid_long_import_line_triggers_split():
    # This test triggers the lines 61-85 branch where a single next_import
    # exceeds line_length when appended, and also tests multi-part import splitting (lines 66-71).
    res = grid(
        imports=["alpha beta gamma"],
        statement="import",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_length=15,
        line_separator="\n",
        white_space="    ",
        include_trailing_comma=False,
    )
    # Let's trace carefully:
    # 1. imports = ["alpha beta gamma"]
    # 2. pops "alpha beta gamma", statement becomes "import(alpha beta gamma" wait:
    #    statement initially: "import " -> statement += "(" + "alpha beta gamma" -> "import (alpha beta gamma"
    #    Wait, imports[0] is popped.
    # Let's pass multiple imports where the second one triggers line 61.
    res = grid(
        imports=["short", "verylongimportname withmultipleparts"],
        statement="import",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_length=20,
        line_separator="\n",
        white_space="    ",
        include_trailing_comma=True,
    )
    assert isinstance(res, str)
    assert res.startswith("import(short")
    assert "verylongimportname" in res
