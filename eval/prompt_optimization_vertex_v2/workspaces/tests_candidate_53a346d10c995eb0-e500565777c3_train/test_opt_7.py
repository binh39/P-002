# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 138], [141, 142], [141, 144]]}

import pytest
from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_no_wrap_short_content():
    config = Config(line_length=40)
    assert line("import os", "\n", config) == "import os"


def test_line_noqa_mode_adds_noqa():
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "import very_long_module_name"
    result = line(content, "\n", config)
    assert result == f"import very_long_module_name{config.comment_prefix} NOQA"


def test_line_noqa_mode_already_has_noqa():
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "import very_long_module_name # NOQA"
    result = line(content, "\n", config)
    assert result == content


def test_line_splitter_at_start_skipped():
    config = Config(line_length=5)
    # Starts with "import ", so line_without_comment.strip().startswith(splitter) is True
    content = "import very_long_name_here"
    result = line(content, "\n", config)
    assert result == content


def test_line_with_comment_and_parentheses_noqa():
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "from a import b, c # noqa: E501"
    result = line(content, "\n", config)
    assert "noqa" in result


def test_line_with_comment_no_parentheses_noqa():
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "from a import b # noqa: E501"
    result = line(content, "\n", config)
    assert "noqa" in result


def test_line_use_parentheses_as_splitter():
    config = Config(
        line_length=5,
        use_parentheses=True,
        include_trailing_comma=False,
    )
    content = "module_a as module_b_very_long"
    result = line(content, "\n", config)
    assert "as" in result


def test_line_use_parentheses_vertical_grid_grouped():
    config = Config(
        line_length=5,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
    )
    content = "from a import alpha, beta, gamma, delta, epsilon"
    result = line(content, "\n", config)
    assert "\n" in result


def test_line_use_parentheses_other_mode():
    config = Config(
        line_length=5,
        use_parentheses=True,
        include_trailing_comma=False,
        multi_line_output=Modes.GRID,
    )
    content = "from a import alpha, beta, gamma, delta, epsilon"
    result = line(content, "\n", config)
    assert "\n" in result


def test_line_no_parentheses_backslash_wrap():
    config = Config(
        line_length=5,
        use_parentheses=False,
    )
    content = "from a import alpha, beta, gamma, delta, epsilon"
    result = line(content, "\n", config)
    assert "\\" in result


def test_line_empty_content_after_pop():
    config = Config(
        line_length=2,
        use_parentheses=False,
    )
    content = "from a import b"
    result = line(content, "\n", config)
    assert isinstance(result, str)


def test_line_comment_prefix_in_last_line_with_parentheses():
    config = Config(
        line_length=5,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "from a import alpha, beta # mycomment"
    result = line(content, "\n", config)
    assert "mycomment" in result
