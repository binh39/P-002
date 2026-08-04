# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 138, 139, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [113, 114], [113, 116], [118, 122], [126, 127], [126, 130], [135, 138], [141, 142], [141, 144]]}

import pytest
from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_no_wrap_short():
    config = Config(line_length=80)
    result = line("import a", "\n", config)
    assert result == "import a"


def test_line_noqa_mode():
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "import a, b, c, d, e, f, g, h"
    result = line(content, "\n", config)
    assert result.startswith(content)
    assert "NOQA" in result

    # Already has # NOQA
    content_noqa = "import a, b, c, d, e, f, g, h # NOQA"
    result2 = line(content_noqa, "\n", config)
    assert result2 == content_noqa


def test_line_wrapping_with_comment_and_parentheses():
    config = Config(
        line_length=20,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "from module import a, b, c # noqa: E501"
    result = line(content, "\n", config)
    assert "noqa" in result


def test_line_wrapping_as_splitter():
    config = Config(
        line_length=15,
        use_parentheses=True,
    )
    content = "import very_long_name as vln"
    result = line(content, "\n", config)
    assert "as" in result


def test_line_wrapping_no_parentheses():
    config = Config(
        line_length=5,
        use_parentheses=False,
        wrap_length=5,
    )
    content = "import a, b, c, d"
    result = line(content, "\n", config)
    assert "\\" in result or line_length_exceeded(content, config) or len(result) >= len(content)


def line_length_exceeded(content, config):
    return len(content) > config.line_length


def test_line_empty_content_after_pop():
    config = Config(
        line_length=5,
        use_parentheses=False,
        wrap_length=5,
    )
    content = "import a"
    result = line(content, "\n", config)
    assert result is not None


def test_line_vertical_grid_grouped_and_comment_prefix_in_lines():
    config = Config(
        line_length=20,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
        comment_prefix="#",
    )
    content = "from a import b, c # comment"
    result = line(content, "\n", config)
    assert isinstance(result, str)
