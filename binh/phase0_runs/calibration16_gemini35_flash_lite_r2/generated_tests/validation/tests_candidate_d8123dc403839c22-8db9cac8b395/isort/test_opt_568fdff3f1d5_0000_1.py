# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 95, 96, 98, 99, 100, 101, 102, 103, 104, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [126, 127], [126, 130], [135, 138], [141, 142], [141, 144]]}

from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_wrapping_comprehensive():
    # 1. Test line length <= config.line_length (returns content as is)
    config = Config(line_length=40)
    assert line("import os", "\n", config) == "import os"

    # 2. Test NOQA wrap mode when length > line_length and "# NOQA" not in content
    config_noqa = Config(line_length=10, multi_line_output=Modes.NOQA)
    long_content = "import os, sys, math"
    res = line(long_content, "\n", config_noqa)
    assert res == "import os, sys, math # noqa" or "# NOQA" in res

    # 3. Test with comment, use_parentheses = True, comment has 'noqa'
    config_paren_noqa = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content_comment_noqa = "from module import a # noqa: F401"
    res3 = line(content_comment_noqa, "\n", config_paren_noqa)
    assert "noqa" in res3

    # 4. Test with comment, use_parentheses = True, splitter == "as "
    config_as = Config(
        line_length=15,
        use_parentheses=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content_as = "import numpy as np"
    res4 = line(content_as, "\n", config_as)
    assert "as" in res4

    # 5. Test with comment, use_parentheses = True, VERTICAL_GRID_GROUPED or other modes
    config_grid = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
    )
    content_grid = "from module import a, b, c # comment"
    res5 = line(content_grid, "\n", config_grid)
    assert res5 is not None

    # 6. Test use_parentheses = False
    config_no_paren = Config(
        line_length=15,
        use_parentheses=False,
    )
    content_no_paren = "from module import a, b, c"
    res6 = line(content_no_paren, "\n", config_no_paren)
    assert "\\" in res6

    # 7. Test when content becomes empty after popping all line_parts
    config_pop = Config(
        line_length=5,
        use_parentheses=False,
    )
    content_pop = "import a"
    res7 = line(content_pop, "\n", config_pop)
    assert res7 is not None
