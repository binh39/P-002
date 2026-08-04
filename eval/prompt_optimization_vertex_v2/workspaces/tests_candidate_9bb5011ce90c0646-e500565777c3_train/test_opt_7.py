# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [126, 127], [126, 130], [135, 138], [141, 142], [141, 144]]}

import pytest
from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_no_wrap_needed():
    # len(content) <= config.line_length -> returns content directly (line 144)
    config = Config(line_length=40)
    result = line("import os", "\n", config)
    assert result == "import os"


def test_line_noqa_mode_adds_noqa():
    # len(content) > config.line_length and wrap_mode == Modes.NOQA and "# NOQA" not in content (lines 141-142)
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    result = line("import very_long_module_name", "\n", config)
    assert result == f"import very_long_module_name{config.comment_prefix} NOQA"


def test_line_noqa_mode_already_has_noqa():
    # len(content) > config.line_length and wrap_mode == Modes.NOQA but "# NOQA" is in content -> returns content (line 144)
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "import very_long_module_name # NOQA"
    result = line(content, "\n", config)
    assert result == content


def test_line_splitter_matching_comment_and_parentheses():
    # Exercises comment handling, comma_maybe, use_parentheses = True, splitter != "as "
    config = Config(
        line_length=20,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "from module import a, b, c # comment"
    result = line(content, "\n", config)
    assert "import" in result
    assert "comment" in result


def test_line_splitter_as_splitter():
    # Exercises splitter == "as " with use_parentheses = True (lines 113-114)
    config = Config(
        line_length=20,
        use_parentheses=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "import a as very_long_alias_name"
    result = line(content, "\n", config)
    assert "as" in result


def test_line_use_parentheses_noqa_in_comment():
    # Exercises comment and "noqa" in comment branch (lines 126-129)
    config = Config(
        line_length=20,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
    )
    content = "from module import a, b # noqa: E501"
    result = line(content, "\n", config)
    assert "noqa" in result


def test_line_comment_prefix_in_lines_last():
    # Exercises lines[-1] adjustment when comment_prefix is in lines[-1] and ends with ')' (lines 135-137)
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=False,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    # Craft content so that comment ends up on the last line with a closing paren
    content = "from mod import a, b # comment"
    result = line(content, "\n", config)
    assert ")" in result


def test_line_no_parentheses_backslash_wrap():
    # Exercises use_parentheses = False (line 140)
    config = Config(
        line_length=15,
        use_parentheses=False,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "from module import long_name_item"
    result = line(content, "\n", config)
    assert "\\" in result


def test_line_empty_content_after_pop():
    # Exercises `if not content: content = next_line.pop()` (lines 104-105)
    config = Config(
        line_length=5,
        use_parentheses=False,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "import a"
    result = line(content, "\n", config)
    assert result is not None
