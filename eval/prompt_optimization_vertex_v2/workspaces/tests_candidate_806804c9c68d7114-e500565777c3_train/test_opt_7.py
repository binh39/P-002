# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}

import pytest
from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_no_wrap_needed():
    # len(content) <= line_length
    config = Config(line_length=20)
    result = line("short", "\n", config)
    assert result == "short"


def test_line_noqa_mode_adds_noqa():
    # elif len(content) > config.line_length and wrap_mode == Modes.NOQA and "# NOQA" not in content
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "very_long_content_here"
    result = line(content, "\n", config)
    assert result == f"{content}{config.comment_prefix} NOQA"


def test_line_noqa_mode_already_has_noqa():
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "very_long_content_here # NOQA"
    result = line(content, "\n", config)
    assert result == content


def test_line_splitter_matching_start():
    # line_without_comment.strip().startswith(splitter) -> True, should skip splitter and return content
    config = Config(line_length=10)
    content = "import os, sys, math"
    result = line(content, "\n", config)
    assert result == content


def test_line_wrap_with_comment_and_parentheses_and_noqa():
    # Covers: comment and "noqa" in comment branch, use_parentheses=True, etc.
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "from module import name # noqa: E501"
    res = line(content, "\n", config)
    assert "noqa" in res


def test_line_wrap_as_splitter():
    # Covers splitter == "as " with use_parentheses=True
    config = Config(
        line_length=10,
        use_parentheses=True,
    )
    content = "import very_long_name as vln"
    res = line(content, "\n", config)
    assert "as" in res


def test_line_wrap_vertical_grid_grouped():
    # Covers wrap_mode in (VERTICAL_HANGING_INDENT, VERTICAL_GRID_GROUPED) and comment manipulation at the end
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
        comment_prefix="#",
    )
    content = "from mod import a, b # comment"
    res = line(content, "\n", config)
    assert res is not None


def test_line_wrap_without_parentheses():
    # Covers use_parentheses=False return branch
    config = Config(
        line_length=10,
        use_parentheses=False,
    )
    content = "from mod import a, b"
    res = line(content, "\n", config)
    assert "\\" in res


def test_line_empty_content_after_pop():
    # Covers not content -> content = next_line.pop()
    config = Config(
        line_length=5,
        use_parentheses=False,
    )
    content = "import a"
    res = line(content, "\n", config)
    assert res is not None


def test_line_comment_without_noqa_and_trailing_comma():
    # Covers comment and not (config.use_parentheses and "noqa" in comment)
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=True,
    )
    content = "from mod import a, b # mycomment"
    res = line(content, "\n", config)
    assert "# mycomment" in res


def test_line_comment_with_parentheses_and_noqa():
    # Covers config.use_parentheses and "noqa" in comment inside the comment block
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=False,
    )
    content = "from mod import a, b # noqa"
    res = line(content, "\n", config)
    assert "noqa" in res
