# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 89, 90, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [126, 127], [135, 138], [141, 142], [141, 144]]}

from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_wrap_basic_and_noqa_branches():
    # Test line length not exceeded -> returns content as-is (line 144)
    short_content = "import a"
    assert line(short_content, "\n", Config(line_length=20)) == short_content

    # Test wrap_mode == Modes.NOQA and '# NOQA' not in content (lines 141-142)
    long_content = "import very_long_module_name_that_exceeds_line_length"
    cfg_noqa = Config(line_length=10, multi_line_output=Modes.NOQA)
    res_noqa = line(long_content, "\n", cfg_noqa)
    assert "# NOQA" in res_noqa


def test_line_wrap_with_splitters_and_comment():
    # Triggers line splitting with comment and use_parentheses=False, splitter != 'as '
    content = "from module import a, b, c # my comment"
    cfg = Config(
        line_length=15,
        use_parentheses=False,
        include_trailing_comma=True,
        multi_line_output=Modes.HANGING_INDENT,
    )
    res = line(content, "\n", cfg)
    assert "\\" in res


def test_line_wrap_with_parentheses_and_as():
    # Triggers use_parentheses=True and splitter == 'as '
    content = "import something as something_else"
    cfg = Config(
        line_length=15,
        use_parentheses=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    res = line(content, "\n", cfg)
    assert "as" in res


def test_line_wrap_vertical_grid_grouped_with_noqa_comment():
    # Triggers use_parentheses=True, comment with 'noqa', vertical grid grouped wrap mode
    content = "from module import alpha, beta, gamma # noqa: E501"
    cfg = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
    )
    res = line(content, "\n", cfg)
    assert "noqa" in res


def test_line_wrap_comment_with_noqa_and_comment_prefix_in_last_line():
    # Triggers lines[-1].endswith(')') and comment_prefix check
    content = "from module import alpha, beta # noqa"
    cfg = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
        comment_prefix="#",
    )
    res = line(content, "\n", cfg)
    assert res is not None


def test_line_wrap_empty_content_after_pop():
    # Triggers not content: content = next_line.pop()
    content = "import a"
    cfg = Config(
        line_length=2,
        use_parentheses=False,
        multi_line_output=Modes.HANGING_INDENT,
    )
    res = line(content, "\n", cfg)
    assert res is not None
