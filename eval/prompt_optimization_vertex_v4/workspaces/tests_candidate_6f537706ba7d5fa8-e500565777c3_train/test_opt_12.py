# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 89, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 107, 108, 109, 110, 112, 113, 114, 116, 118, 124, 125, 126, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 124], [126, 130], [135, 136], [141, 142], [141, 144]]}

import pytest
from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes

def test_line_no_wrap_short_content():
    config = Config(line_length=40)
    res = line("import os", "\n", config)
    assert res == "import os"

def test_line_noqa_mode_adds_noqa():
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    res = line("import long", "\n", config)
    assert res == f"import long{config.comment_prefix} NOQA"

def test_line_noqa_mode_already_has_noqa():
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    res = line("import long # NOQA", "\n", config)
    assert res == "import long # NOQA"

def test_line_wrap_with_splitter_and_parentheses_as():
    config = Config(
        line_length=15,
        use_parentheses=True,
        multi_line_output=Modes.VERTICAL,
    )
    content = "a as b_very_long"
    res = line(content, "\n", config)
    assert "as" in res

def test_line_wrap_with_splitter_comment_and_noqa_parentheses():
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "import a, b # noqa"
    res = line(content, "\n", config)
    assert "# noqa" in res

def test_line_wrap_vertical_grid_grouped_with_comment():
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=False,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
    )
    content = "import a, b # comment"
    res = line(content, "\n", config)
    assert "# comment" in res

def test_line_wrap_backslash_no_parentheses():
    config = Config(
        line_length=5,
        use_parentheses=False,
    )
    # len("import module_very_long") > 5, but splitter must be found and satisfy condition:
    # re.search(exp, line_without_comment) and not line_without_comment.strip().startswith(splitter)
    content = "a.module_very_long"
    res = line(content, "\n", config)
    assert "\\" in res

def test_line_empty_content_after_pop():
    config = Config(
        line_length=2,
        use_parentheses=True,
    )
    content = "import a"
    res = line(content, "\n", config)
    assert "import" in res

def test_line_last_line_comment_parentheses_adjustment():
    config = Config(
        line_length=5,
        use_parentheses=True,
        comment_prefix="#",
        multi_line_output=Modes.VERTICAL,
    )
    # To hit lines 135-137: config.comment_prefix in lines[-1] and lines[-1].endswith(")")
    # We need a comment in the wrapped output where the last line contains the comment prefix and ends with ')'
    content = "a.b # comment"
    res = line(content, "\n", config)
    assert ")" in res
