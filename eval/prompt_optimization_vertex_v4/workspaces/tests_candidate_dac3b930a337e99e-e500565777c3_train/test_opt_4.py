# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 89, 90, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}

from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_wrapping_comprehensive():
    # 1. Test line length <= config.line_length (returns content unmodified)
    short_content = "import a"
    assert line(short_content, "\n") == short_content

    # 2. Test NOQA mode when len > line_length and "# NOQA" not in content
    config_noqa = Config(line_length=10, multi_line_output=Modes.NOQA)
    noqa_content = "import very_long_module_name"
    res = line(noqa_content, "\n", config_noqa)
    assert "NOQA" in res

    # 3. Test NOQA mode when "# NOQA" is already in content (returns unmodified)
    noqa_content_already = "import very_long_module_name  # NOQA"
    assert line(noqa_content_already, "\n", config_noqa) == noqa_content_already

    # 4. Test splitters and comment handling with use_parentheses = False
    config_backslash = Config(
        line_length=15,
        use_parentheses=False,
        include_trailing_comma=True,
    )
    content_bs = "from module import a, b, c # comment"
    res_bs = line(content_bs, "\n", config_backslash)
    assert "\\" in res_bs

    # 5. Test use_parentheses = True with splitter "as "
    config_as = Config(
        line_length=15,
        use_parentheses=True,
    )
    content_as = "import module as mod_alias"
    res_as = line(content_as, "\n", config_as)
    assert "as" in res_as

    # 6. Test use_parentheses = True, vertical hanging indent / grouped, with comment containing noqa
    config_parentheses_vert = Config(
        line_length=15,
        use_parentheses=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
        include_trailing_comma=True,
    )
    content_vert = "from mod import item1, item2 # noqa: E501"
    res_vert = line(content_vert, "\n", config_parentheses_vert)
    assert "(" in res_vert
    assert "noqa" in res_vert

    # 7. Test comment prefix on lines[-1] ending with ')' when comment is present and lines[-1] contains comment_prefix and ')'
    # This specifically exercises lines 135-137
    config_paren_comment = Config(
        line_length=10,
        use_parentheses=True,
        multi_line_output=Modes.GRID,
        include_trailing_comma=False,
        comment_prefix="#",
    )
    # Construct a case where the wrapped lines end up with a comment on the closing parenthesis line
    content_special = "from a import b, c # comment"
    res_special = line(content_special, "\n", config_paren_comment)
    assert isinstance(res_special, str)

    # 8. Test when content becomes empty during while loop and triggers `if not content: content = next_line.pop()`
    config_empty_content = Config(
        line_length=5,
        use_parentheses=False,
    )
    content_empty = "import a"
    res_empty = line(content_empty, "\n", config_empty_content)
    assert isinstance(res_empty, str)
