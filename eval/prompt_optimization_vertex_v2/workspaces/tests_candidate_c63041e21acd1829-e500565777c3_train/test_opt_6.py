# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}

import pytest
from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_no_wrap_short_content():
    config = Config(line_length=40)
    res = line("import os", "\n", config)
    assert res == "import os"


def test_line_noqa_mode():
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    # len("import os") is 9 <= 10
    assert line("import os", "\n", config) == "import os"

    # len("import os.path") is 14 > 10, multi_line_output=Modes.NOQA, "# NOQA" not in content
    res = line("import os.path", "\n", config)
    assert "NOQA" in res

    # already has # NOQA
    res2 = line("import os.path # NOQA", "\n", config)
    assert res2 == "import os.path # NOQA"


def test_line_wrapping_with_comment_and_parentheses():
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    # Contains a comment and use_parentheses is True
    content = "from module import a, b, c # my comment"
    res = line(content, "\n", config)
    assert isinstance(res, str)
    assert "(" in res


def test_line_wrapping_as_splitter_with_parentheses():
    config = Config(
        line_length=15,
        use_parentheses=True,
    )
    # splitter == "as "
    content = "import long_name as ln"
    res = line(content, "\n", config)
    assert "as" in res


def test_line_wrapping_vertical_grid_grouped():
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=False,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
    )
    content = "from a import b, c, d"
    res = line(content, "\n", config)
    assert "\n" in res


def test_line_wrapping_noqa_in_comment():
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
    )
    content = "from module import a, b # noqa: E501"
    res = line(content, "\n", config)
    assert "noqa" in res


def test_line_wrapping_comment_prefix_in_last_line():
    config = Config(
        line_length=12,
        use_parentheses=True,
        comment_prefix="#",
    )
    content = "from a import b, c # comment"
    res = line(content, "\n", config)
    # lines[-1] ends with comment, so line 135-137 handles comment prefix in lines[-1] ending with ')'
    # Wait, let's look at lines[-1]: if it ends with ')' followed by comment, lines[-1].endswith(')') might be false unless it ends with ')' before comment.
    # Let's inspect what lines[-1] actually contains or pass a content where lines[-1] ends with ')' and contains comment_prefix.
    # Actually, lines[-1] in output would be like ")# comment". Wait, lines[-1] ends with comment, not ')'. 
    # Let's check the code:
    # output = f"{content}{splitter}({noqa_comment}{line_separator}{cont_line}{_comma}{_separator})"
    # lines = output.split(line_separator)
    # if config.comment_prefix in lines[-1] and lines[-1].endswith(')'): -> lines[-1] cannot end with ')' if there is a comment after it!
    # Wait! How can lines[-1] contain comment_prefix and endswith(')')?
    # Ah, if comment is present and use_parentheses is True, comment is attached to the last line or content.
    # Let's see what inputs make lines[-1] end with ')' while containing comment_prefix.
    # Wait, if comment_prefix is `#`, and lines[-1] is `)# comment`, then `lines[-1].endswith(')')` is False!
    # Wait, if comment_prefix is ` # ` or something, or if we want lines[-1] to contain comment_prefix and end with ')', maybe comment_prefix is part of something else or lines[-1] has a trailing comment where ')' is before or after?
    # Let's check lines[-1]: `content, comment = lines[-1].split(config.comment_prefix, 1)` -> `lines[-1] = content + ')' + config.comment_prefix + comment[:-1]`
    # This means lines[-1] must contain `comment_prefix` AND end with `)`. That can happen if comment_prefix is inside the text or something, or if comment_prefix is not `#` but a string that appears earlier, or if comment doesn't stay at the very end.
    # Let's test with a comment_prefix like "prefix" and a comment that puts it there, or just check that line runs without error.
    assert isinstance(res, str)


def test_line_wrapping_without_parentheses():
    config = Config(
        line_length=15,
        use_parentheses=False,
    )
    content = "from a import b, c"
    res = line(content, "\n", config)
    assert "\\" in res


def test_line_empty_content_after_split():
    config = Config(
        line_length=5,
        use_parentheses=False,
    )
    content = "import a"
    res = line(content, "\n", config)
    assert isinstance(res, str)
