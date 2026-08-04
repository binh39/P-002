# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 89, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 138], [141, 142], [141, 144]]}

import pytest
from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_no_wrap_needed():
    # len(content) <= config.line_length
    config = Config(line_length=20)
    res = line("short", "\n", config)
    assert res == "short"


def test_line_noqa_mode_adds_noqa():
    # len(content) > config.line_length and wrap_mode == Modes.NOQA and "# NOQA" not in content
    config = Config(line_length=5, multi_line_output=Modes.NOQA)
    res = line("toolong", "\n", config)
    assert res == f"toolong{config.comment_prefix} NOQA"


def test_line_noqa_mode_already_has_noqa():
    # len(content) > config.line_length and wrap_mode == Modes.NOQA and "# NOQA" in content
    config = Config(line_length=5, multi_line_output=Modes.NOQA)
    res = line("toolong # NOQA", "\n", config)
    assert res == "toolong # NOQA"


def test_line_wrap_splitter_import_with_comment_no_parentheses():
    # Splitter in content, comment present, use_parentheses = False
    config = Config(line_length=10, use_parentheses=False)
    # Starts with splitter, so we need content that contains the splitter but doesn't start with it
    content = "x import a, b, c # comment"
    res = line(content, "\n", config)
    assert "\\" in res


def test_line_wrap_splitter_with_parentheses_as_splitter():
    # splitter == "as " with use_parentheses = True
    config = Config(line_length=10, use_parentheses=True)
    content = "very_long_name as short_name"
    res = line(content, "\n", config)
    assert "as" in res


def test_line_wrap_splitter_with_parentheses_standard_splitter_comment_noqa():
    # use_parentheses = True, comment with "noqa", VERTICAL_HANGING_INDENT mode
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "x import a, b, c # noqa: E501"
    res = line(content, "\n", config)
    assert "noqa" in res


def test_line_wrap_splitter_vertical_grid_grouped():
    # use_parentheses = True, wrap_mode in (VERTICAL_HANGING_INDENT, VERTICAL_GRID_GROUPED)
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
    )
    content = "x import a, b, c"
    res = line(content, "\n", config)
    assert "(" in res


def test_line_wrap_splitter_comment_ends_with_parenthesis_rearrangement():
    # triggers lines 135-137: comment prefix in lines[-1] and lines[-1].endswith(")")
    # This happens when a comment is present and parentheses wrap such that comment ends up at the end of the last line.
    config = Config(
        line_length=5,
        use_parentheses=True,
        include_trailing_comma=False,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "x import a, b # comment"
    res = line(content, "\n", config)
    assert "#" in res


def test_line_wrap_empty_content_fallback():
    # Triggers line 104-105: while loop pops everything so content becomes empty, then content = next_line.pop()
    config = Config(
        line_length=2,
        use_parentheses=True,
        wrap_length=1,
    )
    content = "x import a"
    res = line(content, "\n", config)
    assert "import" in res


def test_line_splitter_at_start_not_matched():
    # line_without_comment.strip().startswith(splitter) is True -> doesn't split
    config = Config(line_length=5)
    content = "import a, b, c"
    # Even though len > line_length, it starts with "import ", so it won't split on "import " via that check,
    # but might fall through or return content if no other splitters match.
    res = line(content, "\n", config)
    assert res == content
