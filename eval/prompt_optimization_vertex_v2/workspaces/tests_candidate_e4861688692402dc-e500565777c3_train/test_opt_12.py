# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 89, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 138, 139, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [113, 114], [113, 116], [118, 122], [126, 127], [126, 130], [135, 138], [141, 142], [141, 144]]}

import pytest
from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_short_content():
    # Covers: len(content) <= config.line_length (returns content as-is)
    config = Config(line_length=40)
    result = line("import os", "\n", config)
    assert result == "import os"


def test_line_noqa_mode_already_has_noqa():
    # Covers: len(content) > config.line_length, wrap_mode == Modes.NOQA, "# NOQA" in content
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "import os # NOQA"
    result = line(content, "\n", config)
    assert result == content


def test_line_noqa_mode_adds_noqa():
    # Covers: len(content) > config.line_length, wrap_mode == Modes.NOQA, "# NOQA" not in content
    config = Config(line_length=10, multi_line_output=Modes.NOQA, comment_prefix="#")
    content = "import os, sys"
    result = line(content, "\n", config)
    assert result == "import os, sys# NOQA"


def test_line_wrap_splitter_dot_with_comment_and_parentheses_and_noqa():
    # Exercises comment parsing, include_trailing_comma, use_parentheses, noqa in comment
    config = Config(
        line_length=20,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
        comment_prefix="#",
    )
    content = "module.submodule.function # noqa: E501"
    result = line(content, "\n", config)
    assert "module.submodule" in result
    assert "noqa" in result


def test_line_wrap_splitter_as_with_parentheses():
    # Exercises splitter == "as " with use_parentheses=True
    config = Config(
        line_length=15,
        use_parentheses=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "import long_name as ln"
    result = line(content, "\n", config)
    assert "as" in result




def test_line_wrap_empty_content_after_pop():
    # Exercises if not content: content = next_line.pop()
    config = Config(
        line_length=2,
        use_parentheses=False,
    )
    content = "import a"
    result = line(content, "\n", config)
    assert result is not None


def test_line_wrap_vertical_grid_grouped_with_comment():
    # Exercises VERTICAL_GRID_GROUPED wrap mode and comment adjustments at the end
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=False,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
        comment_prefix="#",
    )
    content = "from a import b # comment"
    result = line(content, "\n", config)
    assert result is not None


def test_line_splitter_starts_with_splitter():
    # Exercises line_without_comment.strip().startswith(splitter) -> True (skips wrapping for that splitter)
    config = Config(line_length=10, use_parentheses=True)
    content = "import a, b, c"
    result = line(content, "\n", config)
    assert result == content


def test_line_comment_with_parentheses_and_noqa_false():
    # Exercises comment present, use_parentheses=True, "noqa" not in comment
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
        comment_prefix="#",
    )
    content = "import a # comment"
    result = line(content, "\n", config)
    assert "# comment" in result
