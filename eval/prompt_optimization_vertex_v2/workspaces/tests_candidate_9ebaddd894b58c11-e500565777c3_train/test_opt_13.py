# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [141, 142], [141, 144]]}

from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_no_wrap_needed():
    # len(content) <= config.line_length -> returns content as is
    config = Config(line_length=40)
    content = "import os"
    assert line(content, "\n", config) == content


def test_line_noqa_mode_with_noqa():
    # len(content) > config.line_length, wrap_mode == Modes.NOQA, "# NOQA" in content -> returns content as is
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "import very_long_module_name # NOQA"
    assert line(content, "\n", config) == content


def test_line_noqa_mode_without_noqa():
    # len(content) > config.line_length, wrap_mode == Modes.NOQA, "# NOQA" not in content -> appends comment_prefix + " NOQA"
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "import very_long_module_name"
    expected = f"import very_long_module_name{config.comment_prefix} NOQA"
    assert line(content, "\n", config) == expected


def test_line_wrap_splitter_dot_no_parentheses():
    # Splitter "." with use_parentheses=False
    config = Config(line_length=15, use_parentheses=False, line_ending="\n")
    content = "module.submodule.attribute"
    # Reaches backslash continuation
    res = line(content, "\n", config)
    assert "\\" in res


def test_line_wrap_splitter_as_with_parentheses():
    # Splitter "as " with use_parentheses=True
    config = Config(line_length=15, use_parentheses=True)
    content = "import long_name as ln"
    res = line(content, "\n", config)
    assert "as" in res


def test_line_wrap_splitter_import_with_comment_and_noqa_in_comment():
    # comment and "noqa" in comment, use_parentheses=True
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "import a, b # noqa: E501"
    res = line(content, "\n", config)
    assert "noqa" in res


def test_line_wrap_splitter_import_with_comment_no_noqa():
    # comment present, but "noqa" not in comment, use_parentheses=True
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
    )
    content = "import a, b # comment"
    res = line(content, "\n", config)
    assert "comment" in res




def test_line_wrap_splitter_empty_content_fallback():
    # Forces not content after while loop -> content = next_line.pop()
    config = Config(
        line_length=5,
        wrap_length=5,
        use_parentheses=False,
    )
    content = "import a"
    res = line(content, "\n", config)
    assert "import" in res


def test_line_comment_with_comment_prefix_in_last_line():
    # Triggering lines[-1] contains comment_prefix and ends with ')'
    config = Config(
        line_length=10,
        use_parentheses=True,
        comment_prefix="#",
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "import foo, bar # comment"
    res = line(content, "\n", config)
    assert res is not None
