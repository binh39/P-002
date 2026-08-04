# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [126, 127], [126, 130], [135, 138], [141, 142], [141, 144]]}

from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_wrap_no_split_or_short():
    config = Config(line_length=40)
    assert line("import a", "\n", config) == "import a"


def test_line_wrap_noqa_mode_missing_noqa():
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "import very_long_module_name"
    result = line(content, "\n", config)
    assert result == content + f"{config.comment_prefix} NOQA"


def test_line_wrap_noqa_mode_already_has_noqa():
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "import very_long_module_name  # NOQA"
    assert line(content, "\n", config) == content


def test_line_wrap_with_comment_and_noqa():
    config = Config(
        line_length=20,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "from module import a, b, c  # noqa: E501"
    res = line(content, "\n", config)
    assert "noqa" in res


def test_line_wrap_splitter_as_with_parentheses():
    config = Config(
        line_length=15,
        use_parentheses=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "import foo as bar_baz_long"
    res = line(content, "\n", config)
    assert "as" in res


def test_line_wrap_empty_content_after_while():
    # To hit lines 104-105:
    # `len(content) + 2 > (config.wrap_length or config.line_length) and line_parts`
    # must be True initially, pops parts until `line_parts` is exhausted and `content` becomes empty.
    # E.g., splitter is "import ", content is "import a", line_length=2.
    # line_parts = ["", "a"]
    # 1st iteration: next_line.append("a"), content = "import " (len 7 + 2 > 2).
    # 2nd iteration: next_line.append(""), content = "import" (len 6 + 2 > 2). Wait, let's trace carefully:
    # If line_parts = ["", "a"], splitter.join([""]) is "".
    config = Config(
        line_length=1,
        use_parentheses=False,
    )
    content = "import a"
    res = line(content, "\n", config)
    assert res is not None


def test_line_wrap_vertical_grid_grouped_and_comment_adjustment():
    config = Config(
        line_length=20,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
    )
    content = "from mod import alpha, beta  # comment"
    res = line(content, "\n", config)
    assert res is not None


def test_line_wrap_splitter_dot_no_parentheses():
    config = Config(
        line_length=10,
        use_parentheses=False,
    )
    content = "module.submodule.attribute"
    res = line(content, "\n", config)
    assert "\\" in res
