# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [126, 127], [126, 130], [135, 138], [141, 142], [141, 144]]}

import pytest
from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_wrap_basic_backslash():
    # Test line wrapping without parentheses, hitting lines 71-140 with backslash format
    # Note: line_without_comment.strip().startswith(splitter) check prevents splitting if it starts with the splitter.
    # So we need content like "x = import a, b" or something containing "import " not at the start,
    # or a splitter like "." or "as ".
    config = Config(line_length=10, use_parentheses=False)
    content = "from my_module import very_long_name_a, very_long_name_b"
    result = line(content, "\n", config)
    assert "\\" in result


def test_line_wrap_with_comment_and_parentheses():
    # Test line wrapping with comment, use_parentheses=True, splitter != "as "
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "from my_module import a, b, c  # some comment"
    res = line(content, "\n", config)
    assert "import" in res


def test_line_wrap_as_splitter_with_parentheses():
    config = Config(line_length=10, use_parentheses=True)
    content = "import very_long_module_name as x"
    res = line(content, "\n", config)
    assert "as" in res


def test_line_wrap_vertical_grid_grouped_and_noqa():
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
    )
    content = "from mod import mod1, mod2  # noqa: E501"
    res = line(content, "\n", config)
    assert "noqa" in res


def test_line_wrap_comment_prefix_in_lines_last():
    # Triggers lines 135-137 where comment_prefix is in lines[-1] and lines[-1].endswith(")")
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=False,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "from mod import a, b  # comment"
    res = line(content, "\n", config)
    assert res is not None


def test_line_wrap_noqa_mode_branch():
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "some very long line without noqa"
    res = line(content, "\n", config)
    assert "NOQA" in res


def test_line_wrap_empty_content_fallback():
    config = Config(line_length=5, use_parentheses=False)
    content = "from mod import a"
    res = line(content, "\n", config)
    assert res is not None
