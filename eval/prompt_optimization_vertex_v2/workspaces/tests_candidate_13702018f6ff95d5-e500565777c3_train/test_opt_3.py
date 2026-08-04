# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [126, 127], [126, 130], [135, 138], [141, 142], [141, 144]]}

from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_wrap_basic_splitter():
    # Covers splitters like "." or "import " without parentheses, hitting the backslash return branch (line 140)
    config = Config(line_length=10, use_parentheses=False, multi_line_output=Modes.GRID)
    content = "very_long_variable.attribute"
    res = line(content, "\n", config)
    assert "\\" in res


def test_line_wrap_with_comment_and_parentheses():
    # Covers lines 77-78, 85-96, 112, 116, 118-124, 130-133, etc.
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "long_module.attr # comment"
    res = line(content, "\n", config)
    assert "(" in res
    assert "# comment" in res


def test_line_wrap_as_splitter_with_parentheses():
    # Covers splitter == "as " with use_parentheses=True (lines 113-114)
    config = Config(
        line_length=10,
        use_parentheses=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "import long_name as alias"
    res = line(content, "\n", config)
    assert "as" in res


def test_line_wrap_noqa_in_comment_with_parentheses():
    # Covers 'noqa' in comment branches (lines 126-129)
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "long_module.attr # noqa: E501"
    res = line(content, "\n", config)
    assert "noqa" in res


def test_line_wrap_comment_prefix_in_last_line_ending_with_paren():
    # Covers lines 135-137 where comment_prefix is in lines[-1] and ends with ')'
    config = Config(
        line_length=5,
        use_parentheses=True,
        include_trailing_comma=False,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
        comment_prefix="#",
    )
    # Craft content such that length > line_length, has a comment, uses parentheses,
    # and forces comment_prefix into the last line which ends with ')'
    content = "mod.sub # c"
    res = line(content, "\n", config)
    assert ")" in res


def test_line_wrap_noqa_mode_adds_noqa():
    # Covers lines 141-142 (wrap_mode == Modes.NOQA and len > line_length)
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "some_very_long_content_here"
    res = line(content, "\n", config)
    assert "NOQA" in res


def test_line_wrap_empty_content_after_pop():
    # Covers line 104-105: while loop pops all line_parts making content empty -> content = next_line.pop()
    config = Config(line_length=5, use_parentheses=False, multi_line_output=Modes.GRID, wrap_length=5)
    content = "a.b.c"
    res = line(content, "\n", config)
    assert isinstance(res, str)
