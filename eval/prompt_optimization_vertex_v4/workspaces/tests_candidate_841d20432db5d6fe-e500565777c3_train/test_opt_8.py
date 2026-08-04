# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 89, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}

import pytest
from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_no_wrap_short():
    # len(content) <= config.line_length -> returns content directly
    content = "import os"
    res = line(content, "\n", Config(line_length=20))
    assert res == content


def test_line_noqa_mode():
    # len(content) > config.line_length and wrap_mode == Modes.NOQA and '# NOQA' not in content
    content = "import very_long_module_name_that_exceeds_length"
    config = Config(line_length=20, multi_line_output=Modes.NOQA)
    res = line(content, "\n", config)
    assert res == f"{content}{config.comment_prefix} NOQA"


def test_line_noqa_mode_already_present():
    # len(content) > config.line_length and wrap_mode == Modes.NOQA and '# NOQA' in content -> returns content
    content = "import very_long_module_name_that_exceeds_length # NOQA"
    config = Config(line_length=20, multi_line_output=Modes.NOQA)
    res = line(content, "\n", config)
    assert res == content


def test_line_splitter_starts_with():
    # line_without_comment.strip().startswith(splitter) is True -> skips splitter, continues loop
    content = "import a, b, c, d, e, f, g, h, i, j"
    config = Config(line_length=15, multi_line_output=Modes.GRID)
    res = line(content, "\n", config)
    assert isinstance(res, str)


def test_line_with_comment_no_parentheses_noqa():
    # comment and not (config.use_parentheses and "noqa" in comment)
    content = "from module import a, b # noqa"
    config = Config(line_length=15, use_parentheses=True, multi_line_output=Modes.GRID)
    res = line(content, "\n", config)
    assert isinstance(res, str)


def test_line_empty_content_fallback():
    # content becomes empty after loop, so content = next_line.pop()
    content = "from a import b"
    config = Config(line_length=5, use_parentheses=False, multi_line_output=Modes.GRID)
    res = line(content, "\n", config)
    assert isinstance(res, str)


def test_line_use_parentheses_as_splitter():
    # config.use_parentheses and splitter == "as "
    content = "import long_module_name as lmn"
    config = Config(line_length=15, use_parentheses=True, multi_line_output=Modes.GRID)
    res = line(content, "\n", config)
    assert "as" in res


def test_line_vertical_hanging_indent_or_grouped():
    # wrap_mode in (Modes.VERTICAL_HANGING_INDENT, Modes.VERTICAL_GRID_GROUPED)
    content = "from module import alpha, beta, gamma, delta"
    for mode in (Modes.VERTICAL_HANGING_INDENT, Modes.VERTICAL_GRID_GROUPED):
        config = Config(line_length=20, use_parentheses=True, multi_line_output=mode, include_trailing_comma=True)
        res = line(content, "\n", config)
        assert "\n" in res


def test_line_with_noqa_comment_parentheses():
    # comment and "noqa" in comment with use_parentheses=True
    content = "from module import alpha, beta # noqa: E501"
    config = Config(line_length=15, use_parentheses=True, include_trailing_comma=True, multi_line_output=Modes.GRID)
    res = line(content, "\n", config)
    assert "noqa" in res


def test_line_comment_prefix_in_lines_last_and_ends_with_paren():
    # lines[-1] contains comment_prefix and ends with ')'
    content = "from module import alpha, beta # custom comment"
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=False,
        comment_prefix="#",
        multi_line_output=Modes.GRID,
    )
    res = line(content, "\n", config)
    assert isinstance(res, str)
