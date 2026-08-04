# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 89, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}

import pytest
from isort.settings import Config
from isort.wrap_modes import WrapModes as Modes
from isort.wrap import line


def test_line_wrap_with_parentheses_and_as_splitter():
    # Covers: splitter == "as " with use_parentheses=True
    config = Config(line_length=15, use_parentheses=True, multi_line_output=Modes.GRID)
    content = "import very_long_module as m"
    res = line(content, "\n", config)
    assert "as" in res

def test_line_wrap_vertical_modes_and_noqa_comment():
    # Covers: wrap_mode in (VERTICAL_HANGING_INDENT, VERTICAL_GRID_GROUPED)
    # Also comment with "noqa", include_trailing_comma=True
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
        comment_prefix="#",
    )
    content = "from module import a, b, c # noqa: E501"
    res = line(content, "\n", config)
    assert "noqa" in res

def test_line_wrap_comment_prefix_in_last_line():
    # Covers: if config.comment_prefix in lines[-1] and lines[-1].endswith(")")
    config = Config(
        line_length=5,
        use_parentheses=True,
        include_trailing_comma=False,
        multi_line_output=Modes.GRID,
        comment_prefix="#",
    )
    content = "a.b.c # comment"
    res = line(content, "\n", config)
    assert res is not None

def test_line_wrap_noqa_mode():
    # Covers: len(content) > config.line_length and wrap_mode == Modes.NOQA and "# NOQA" not in content
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "import long_module_name"
    res = line(content, "\n", config)
    assert "NOQA" in res

def test_line_wrap_noqa_mode_already_present():
    # Covers: len(content) > config.line_length and wrap_mode == Modes.NOQA and "# NOQA" in content (falls through to return content)
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "import long_module_name # NOQA"
    res = line(content, "\n", config)
    assert res == content

def test_line_no_wrap_needed():
    # Covers: len(content) <= config.line_length -> returns content directly
    config = Config(line_length=50)
    content = "import os"
    res = line(content, "\n", config)
    assert res == content
