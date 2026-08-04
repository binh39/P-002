# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [126, 127], [135, 138], [141, 142], [141, 144]]}

import re
from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_no_wrap_needed():
    config = Config(line_length=50)
    content = "import os"
    assert line(content, "\n", config) == content


def test_line_noqa_mode_add_noqa():
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "import os, sys, math"
    res = line(content, "\n", config)
    assert " # NOQA" in res


def test_line_noqa_mode_already_has_noqa():
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "import os, sys, math # NOQA"
    assert line(content, "\n", config) == content


def test_line_wrap_with_comment_and_parentheses_noqa():
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "from module import a, b # noqa: E501"
    res = line(content, "\n", config)
    assert res is not None


def test_line_wrap_with_splitter_as_and_parentheses():
    config = Config(
        line_length=10,
        use_parentheses=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "import foo as bar"
    res = line(content, "\n", config)
    assert "as" in res


def test_line_wrap_without_parentheses():
    config = Config(
        line_length=5,
        use_parentheses=False,
    )
    # To satisfy `line_without_comment.strip().startswith(splitter)` being False,
    # the splitter must not be at the start of the line.
    content = "a.b.c.d.e.f"
    res = line(content, "\n", config)
    assert "\\" in res or "\n" in res


def test_line_wrap_vertical_grid_grouped_with_comment():
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
        comment_prefix="#",
    )
    content = "import foo, bar # comment"
    res = line(content, "\n", config)
    assert res is not None


def test_line_empty_content_after_pop():
    config = Config(
        line_length=5,
        use_parentheses=False,
    )
    content = "a.b"
    res = line(content, "\n", config)
    assert res is not None
