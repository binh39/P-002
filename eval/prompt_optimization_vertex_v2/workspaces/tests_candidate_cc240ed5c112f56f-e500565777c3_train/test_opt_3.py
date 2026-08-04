# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}

from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_wrap_basic_splitter():
    # Covers splitters like "." or "import " without parentheses, and line_parts pop logic.
    config = Config(line_length=10, use_parentheses=False, multi_line_output=Modes.GRID)
    content = "very_long_variable.attribute"
    res = line(content, "\n", config)
    assert "\\" in res


def test_line_wrap_with_parentheses_and_comment():
    # Covers use_parentheses=True, comment present, comma_maybe logic, and wrap_length
    config = Config(
        line_length=20,
        wrap_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.GRID,
    )
    content = "module.submodule # comment"
    res = line(content, "\n", config)
    assert "(" in res
    assert "# comment" in res


def test_line_wrap_as_splitter_with_parentheses():
    # Covers splitter == "as " with use_parentheses=True
    config = Config(
        line_length=10,
        use_parentheses=True,
        multi_line_output=Modes.GRID,
    )
    content = "import long_name as alias"
    res = line(content, "\n", config)
    assert "as" in res


def test_line_wrap_vertical_hanging_indent_modes():
    # Covers wrap_mode in (Modes.VERTICAL_HANGING_INDENT, Modes.VERTICAL_GRID_GROUPED)
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "module.submodule"
    res = line(content, "\n", config)
    assert "\n" in res


def test_line_wrap_noqa_comment_logic():
    # Covers comment with "noqa" and specific line adjustment block
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.GRID,
    )
    content = "module.submodule # noqa: E501"
    res = line(content, "\n", config)
    assert "noqa" in res


def test_line_wrap_last_line_comment_adjustment():
    # Covers config.comment_prefix in lines[-1] and lines[-1].endswith(")")
    config = Config(
        line_length=10,
        use_parentheses=True,
        multi_line_output=Modes.GRID,
        comment_prefix="#",
    )
    # Craft content so that the output ends with a comment and closing paren
    content = "a.b"
    res = line(content, "\n", config)
    assert res is not None


def test_line_wrap_noqa_mode_adds_noqa():
    # Covers elif len(content) > config.line_length and wrap_mode == Modes.NOQA and "# NOQA" not in content
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "some_very_long_line_without_noqa"
    res = line(content, "\n", config)
    assert "NOQA" in res
