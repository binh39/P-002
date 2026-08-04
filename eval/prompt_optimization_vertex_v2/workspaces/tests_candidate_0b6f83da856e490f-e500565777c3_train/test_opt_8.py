# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}

import pytest
from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_wrap_basic():
    config = Config(line_length=10, use_parentheses=False)
    content = "from module import name1, name2"
    result = line(content, "\n", config)
    assert "\\" in result


def test_line_wrap_with_comment():
    config = Config(line_length=10, use_parentheses=True, include_trailing_comma=True)
    content = "import module.submodule # comment"
    result = line(content, "\n", config)
    assert "comment" in result


def test_line_wrap_as_splitter():
    config = Config(line_length=10, use_parentheses=True)
    content = "import long_name as ln"
    result = line(content, "\n", config)
    assert "as" in result


def test_line_wrap_vertical_hanging_indent():
    config = Config(
        line_length=10,
        use_parentheses=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
        include_trailing_comma=True,
    )
    content = "import name1.name2.name3"
    result = line(content, "\n", config)
    assert "(" in result


def test_line_wrap_noqa_comment():
    config = Config(
        line_length=10,
        use_parentheses=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
        include_trailing_comma=True,
    )
    content = "import name1.name2 # noqa: F401"
    result = line(content, "\n", config)
    assert "noqa" in result


def test_line_wrap_noqa_mode():
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "import very_long_name_here"
    result = line(content, "\n", config)
    assert "NOQA" in result


def test_line_no_wrap_needed():
    config = Config(line_length=50)
    content = "import short"
    result = line(content, "\n", config)
    assert result == content
