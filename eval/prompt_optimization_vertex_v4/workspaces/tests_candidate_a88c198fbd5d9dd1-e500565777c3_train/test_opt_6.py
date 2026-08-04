# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [126, 127], [126, 130], [135, 138], [141, 142], [141, 144]]}

import pytest
from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_wrap_basic():
    # Test line wrapping without parentheses, using backslash continuation
    config = Config(line_length=10, use_parentheses=False)
    content = "from a import b, c, d, e"
    result = line(content, "\n", config)
    assert "\\" in result


def test_line_wrap_with_comment_and_parentheses():
    # Test with comment, use_parentheses=True, splitter = "."
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "module.submodule.func # comment"
    result = line(content, "\n", config)
    assert "(" in result
    assert "comment" in result


def test_line_wrap_as_splitter_with_parentheses():
    # Test splitter == "as " with use_parentheses=True
    config = Config(line_length=10, use_parentheses=True)
    content = "import long_name as ln"
    result = line(content, "\n", config)
    assert "as" in result


def test_line_wrap_noqa_in_comment():
    # Test comment with noqa and vertical hanging indent / grouped
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
    )
    content = "from module import a # noqa: F401"
    result = line(content, "\n", config)
    assert "noqa" in result


def test_line_wrap_comment_prefix_in_last_line_with_closing_paren():
    # Triggers lines 135-137: config.comment_prefix in lines[-1] and lines[-1].endswith(")")
    # When use_parentheses is True, comment is present (or added), and the last line contains the comment prefix and ends with )
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=False,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
        comment_prefix="#",
    )
    content = "import a, b # c"
    result = line(content, "\n", config)
    assert result is not None


def test_line_noqa_mode():
    # Test elif branch for Modes.NOQA where '# NOQA' not in content
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "import something_very_long"
    result = line(content, "\n", config)
    assert "NOQA" in result


def test_line_noqa_mode_already_has_noqa():
    # Test elif branch when '# NOQA' is already in content
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "import something_very_long # NOQA"
    result = line(content, "\n", config)
    assert result == content
