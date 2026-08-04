# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 138], [141, 142], [141, 144]]}

import pytest
from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_wrap_basic():
    # Test line wrapping without parentheses, splitter in line
    config = Config(line_length=5, use_parentheses=False)
    content = "import a, b, c"
    # To trigger line length wrapping, len(content) > config.line_length is required.
    # Also, the splitter must not be at the start of the line after strip.
    # Let's use a content where "import " is inside or after something, or just use a splitter like "as ".
    content2 = "x import a, b, c"
    res = line(content2, "\n", config)
    assert "\\" in res


def test_line_wrap_with_comment_and_parentheses():
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "x import a, b # comment"
    res = line(content, "\n", config)
    assert "(" in res


def test_line_wrap_with_noqa_comment():
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
    )
    content = "x import a, b # noqa: E501"
    res = line(content, "\n", config)
    assert "noqa" in res


def test_line_wrap_as_splitter():
    config = Config(
        line_length=10,
        use_parentheses=True,
    )
    content = "x import long_name as ln"
    res = line(content, "\n", config)
    assert "as" in res


def test_line_wrap_empty_content_fallback():
    config = Config(
        line_length=2,
        wrap_length=2,
        use_parentheses=False,
    )
    # This forces content to become empty during the while loop pop
    content = "x import a"
    res = line(content, "\n", config)
    assert res


def test_line_wrap_noqa_mode():
    config = Config(
        line_length=10,
        multi_line_output=Modes.NOQA,
    )
    content = "x import a_very_long_name"
    res = line(content, "\n", config)
    assert "NOQA" in res
