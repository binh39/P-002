# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 98], [99, 102], [99, 104], [104, 105], [112, 113], [112, 140], [113, 114], [141, 142], [141, 144]]}

import pytest
from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_wrap_basic():
    # Test line wrapping without parentheses, using backslash continuation.
    # We need len(content) > line_length, use_parentheses = False,
    # and a splitter (like "as " or ".") inside line_without_comment.
    config = Config(line_length=10, use_parentheses=False)
    content = "very_long_module_name as m"
    res = line(content, "\n", config)
    assert "\\" in res


def test_line_wrap_with_comment_and_noqa_parentheses():
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    # splitter "import " with comment containing "noqa"
    content = "import alpha, beta # noqa: E501"
    res = line(content, "\n", config)
    assert "noqa" in res


def test_line_wrap_as_splitter():
    config = Config(
        line_length=10,
        use_parentheses=True,
    )
    content = "import very_long_module as m"
    res = line(content, "\n", config)
    assert "as" in res


def test_line_wrap_vertical_grid_grouped():
    config = Config(
        line_length=10,
        use_parentheses=True,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
        include_trailing_comma=True,
    )
    content = "import alpha, beta, gamma"
    res = line(content, "\n", config)
    assert res is not None


def test_line_wrap_comment_prefix_in_last_line_with_parenthesis():
    # Hits lines 135-137:
    # if config.comment_prefix in lines[-1] and lines[-1].endswith(")"):
    config = Config(
        line_length=15,
        use_parentheses=True,
        comment_prefix="#",
    )
    content = "import a, b # comment"
    res = line(content, "\n", config)
    assert res is not None


def test_line_noqa_mode():
    config = Config(
        line_length=10,
        multi_line_output=Modes.NOQA,
    )
    content = "import very_long_line_here_without_noqa"
    res = line(content, "\n", config)
    assert "NOQA" in res
