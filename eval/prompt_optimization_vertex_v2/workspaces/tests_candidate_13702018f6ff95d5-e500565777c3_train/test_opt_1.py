# file: src\sample_repo\isort\isort\wrap_modes.py:117-167
# asked: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}
# gained: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [146, 147], [146, 167], [153, 156], [153, 157]]}

import pytest
from isort.wrap_modes import hanging_indent

def test_hanging_indent_comprehensive():
    # 1. Test empty imports branch (line 119)
    res_empty = hanging_indent(
        imports=[],
        statement="from module import ",
        line_length=80,
        line_separator="\n",
        indent="    ",
        comments=set(),
        remove_comments=False,
        comment_prefix="#",
    )
    assert res_empty == ""

    # 2. Test first import exceeding line length limit (line 127)
    res_first_long = hanging_indent(
        imports=["very_long_import_name_that_exceeds_limit"],
        statement="from module import ",
        line_length=20,  # line_length_limit = 17
        line_separator="\n",
        indent="    ",
        comments=set(),
        remove_comments=False,
        comment_prefix="#",
    )
    assert "very_long_import_name_that_exceeds_limit" in res_first_long

    # 3. Test multiple imports where subsequent import exceeds line length limit (line 139)
    res_subsequent_long = hanging_indent(
        imports=["a", "very_long_subsequent_import_name_that_exceeds_limit"],
        statement="from module import ",
        line_length=35,  # line_length_limit = 32
        line_separator="\n",
        indent="    ",
        comments=set(),
        remove_comments=False,
        comment_prefix="#",
    )
    assert "\n    very_long_subsequent_import_name_that_exceeds_limit" in res_subsequent_long

    # 4. Test with comments fitting within line length limit (line 153)
    res_comment_fits = hanging_indent(
        imports=["a"],
        statement="from module import ",
        line_length=80,
        line_separator="\n",
        indent="    ",
        comments={"# comment"},
        remove_comments=False,
        comment_prefix="#",
    )
    assert "# comment" in res_comment_fits

    # 5. Test with comments exceeding line length limit, forcing wrap with comment on new line (line 157)
    res_comment_exceeds = hanging_indent(
        imports=["a"],
        statement="from module import a",
        line_length=15,  # line_length_limit = 12, statement len = 20, statement_with_comments exceeds
        line_separator="\n",
        indent="    ",
        comments={"# very long comment that forces wrap"},
        remove_comments=False,
        comment_prefix="#",
    )
    assert "\n    " in res_comment_exceeds
    assert "very long comment" in res_comment_exceeds
