# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [126, 127], [126, 130], [135, 138], [141, 142], [141, 144]]}

import pytest
from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_no_wrap_needed():
    # len(content) <= line_length
    config = Config(line_length=40)
    res = line("import a", "\n", config)
    assert res == "import a"


def test_line_noqa_mode():
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    res = line("import a, b, c, d, e, f", "\n", config)
    assert res == f"import a, b, c, d, e, f{config.comment_prefix} NOQA"

    # Already has # NOQA
    res2 = line(f"import a, b, c, d, e, f{config.comment_prefix} NOQA", "\n", config)
    assert res2 == f"import a, b, c, d, e, f{config.comment_prefix} NOQA"


def test_line_splitter_at_start():
    # content starts with splitter, so re.search succeeds but strip().startswith(splitter) is True,
    # meaning it won't match, falling through to return content.
    config = Config(line_length=5)
    res = line("import a", "\n", config)
    assert res == "import a"


def test_line_basic_wrap_no_parentheses():
    config = Config(line_length=2, use_parentheses=False)
    # "a.b.c" contains "." but does not start with it, and len > line_length
    res = line("a.b.c", "\n", config)
    assert "\\" in res


def test_line_with_comment_and_parentheses():
    config = Config(
        line_length=2,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    # Has comment, use_parentheses=True, noqa NOT in comment
    res = line("a.b.c # my comment", "\n", config)
    assert "# my comment" in res


def test_line_with_noqa_comment_and_parentheses():
    config = Config(
        line_length=2,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    # comment contains "noqa"
    res = line("a.b.c # noqa: E501", "\n", config)
    assert "noqa" in res


def test_line_splitter_as():
    config = Config(
        line_length=2,
        use_parentheses=True,
    )
    res = line("verylongname as short", "\n", config)
    assert " as " in res


def test_line_empty_content_after_pop():
    # Forces not content branch
    config = Config(
        line_length=1,
        use_parentheses=True,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
    )
    res = line("a.b", "\n", config)
    assert res is not None


def test_line_comment_prefix_in_last_line_ending_with_paren():
    config = Config(
        line_length=2,
        use_parentheses=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
        comment_prefix="#",
    )
    res = line("a.b # comment", "\n", config)
    assert isinstance(res, str)
