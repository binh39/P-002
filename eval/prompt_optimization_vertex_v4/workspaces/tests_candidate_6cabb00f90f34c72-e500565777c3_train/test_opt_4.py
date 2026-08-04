# file: src\sample_repo\isort\isort\wrap_modes.py:117-167
# asked: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}
# gained: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [146, 147], [146, 167], [153, 156], [153, 157]]}

from typing import Any
import isort.wrap_modes

def test_hanging_indent_empty_imports():
    res = isort.wrap_modes.hanging_indent(
        imports=[],
        statement="from module import ",
        line_length=80,
        indent="    ",
        line_separator="\n",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
    )
    assert res == ""

def test_hanging_indent_first_import_exceeds_limit():
    # line_length = 15 -> line_length_limit = 12
    # statement = "import " (length 7) + next_import = "verylongimportname" (length 18) -> total 25 > 12
    res = isort.wrap_modes.hanging_indent(
        imports=["verylongimportname"],
        statement="import ",
        line_length=15,
        indent="    ",
        line_separator="\n",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
    )
    assert "verylongimportname" in res

def test_hanging_indent_subsequent_import_exceeds_limit():
    # line_length = 20 -> limit = 17
    # First import fits, second causes wrap in the while loop
    res = isort.wrap_modes.hanging_indent(
        imports=["short", "a_very_long_subsequent_import_name"],
        statement="import ",
        line_length=20,
        indent="    ",
        line_separator="\n",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
    )
    assert "a_very_long_subsequent_import_name" in res

def test_hanging_indent_with_comments_fits():
    res = isort.wrap_modes.hanging_indent(
        imports=["foo"],
        statement="import ",
        line_length=80,
        indent="    ",
        line_separator="\n",
        comments=["# comment"],
        remove_comments=False,
        comment_prefix="#",
    )
    assert "import foo" in res
    assert "# comment" in res

def test_hanging_indent_with_comments_exceeds_limit():
    # Forces statement_with_comments to exceed line_length_limit + 2
    res = isort.wrap_modes.hanging_indent(
        imports=["a" * 70],
        statement="import ",
        line_length=40,
        indent="    ",
        line_separator="\n",
        comments=["# comment"],
        remove_comments=False,
        comment_prefix="# ",
    )
    assert "# comment" in res
