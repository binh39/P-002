# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}

import pytest
from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_no_wrap_short_content():
    # len(content) <= config.line_length
    config = Config(line_length=40)
    result = line("import os", "\n", config)
    assert result == "import os"


def test_line_no_qa_mode_already_has_noqa():
    # len(content) > config.line_length, wrap_mode == Modes.NOQA, "# NOQA" in content
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "import os # NOQA"
    result = line(content, "\n", config)
    assert result == content


def test_line_no_qa_mode_adds_noqa():
    # len(content) > config.line_length, wrap_mode == Modes.NOQA, "# NOQA" not in content
    config = Config(line_length=10, multi_line_output=Modes.NOQA, comment_prefix="#")
    content = "import os, sys"
    result = line(content, "\n", config)
    assert result == "import os, sys# NOQA"


def test_line_wrap_splitter_no_comment_no_parentheses():
    # Triggers line wrapping with a splitter (e.g. "import "), no comment, use_parentheses=False
    config = Config(line_length=15, use_parentheses=False, wrap_length=15)
    content = "from very_long_module import very_long_name"
    # Splitters tried: "import ", "cimport ", ".", "as "
    # "import " matches and splits.
    result = line(content, "\n", config)
    assert "\\" in result
    assert "import \\\n" in result


def test_line_wrap_with_comment_and_parentheses_trailing_comma():
    # Triggers comment parsing, use_parentheses=True, include_trailing_comma=True
    config = Config(
        line_length=20,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL,
        comment_prefix="#",
    )
    content = "from module import a, b # comment"
    result = line(content, "\n", config)
    assert "(" in result
    assert ")" in result
    assert "# comment" in result


def test_line_wrap_with_noqa_comment_in_parentheses():
    # Triggers noqa comment inside parentheses branch: "noqa" in comment
    config = Config(
        line_length=20,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
        comment_prefix="#",
    )
    content = "from module import a, b # noqa: E501"
    result = line(content, "\n", config)
    assert "noqa: E501" in result
    assert ")" in result


def test_line_wrap_splitter_as():
    # Triggers splitter == "as " with use_parentheses=True
    config = Config(
        line_length=15,
        use_parentheses=True,
        multi_line_output=Modes.VERTICAL,
    )
    content = "import something as something_else"
    result = line(content, "\n", config)
    assert "as" in result


def test_line_wrap_vertical_grid_grouped():
    # Triggers wrap_mode in (Modes.VERTICAL_HANGING_INDENT, Modes.VERTICAL_GRID_GROUPED)
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=False,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
    )
    content = "from module import a, b, c"
    result = line(content, "\n", config)
    assert "\n" in result
    assert ")" in result


def test_line_comment_prefix_in_last_line_with_parenthesis():
    # Triggers lines[-1] containing comment_prefix and ending with ')'
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=False,
        multi_line_output=Modes.VERTICAL,
        comment_prefix="#",
    )
    # A line that splits and whose last part ends with a comment, leading to lines[-1] containing '#' and ')'
    content = "from mod import a # comment"
    result = line(content, "\n", config)
    assert ")" in result
    assert "#" in result


def test_line_empty_content_after_pop():
    # Triggers `if not content: content = next_line.pop()`
    # This happens when content before splitter is empty or gets fully popped.
    config = Config(
        line_length=5,
        use_parentheses=False,
        wrap_length=5,
    )
    content = ".attr"
    result = line(content, "\n", config)
    assert result is not None
