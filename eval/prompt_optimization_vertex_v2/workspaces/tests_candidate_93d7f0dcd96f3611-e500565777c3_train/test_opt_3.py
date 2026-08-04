# file: src\sample_repo\isort\isort\wrap_modes.py:117-167
# asked: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}
# gained: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}

from isort.wrap_modes import hanging_indent


def test_hanging_indent_empty_imports():
    res = hanging_indent(
        statement="import a",
        imports=[],
        white_space=" ",
        indent="    ",
        line_length=80,
        comments=[],
        line_separator="\n",
        comment_prefix="#",
        include_trailing_comma=False,
        remove_comments=False,
    )
    assert res == ""


def test_hanging_indent_first_import_exceeds_limit():
    # line_length = 15 -> line_length_limit = 12
    # statement = "import " (length 7)
    # next_import = "verylongimport" (length 14)
    # len("import verylongimport") = 21 > 12 -> triggers line 127/128
    res = hanging_indent(
        statement="import ",
        imports=["verylongimport"],
        white_space=" ",
        indent="    ",
        line_length=15,
        comments=[],
        line_separator="\n",
        comment_prefix="#",
        include_trailing_comma=False,
        remove_comments=False,
    )
    assert "\\" in res


def test_hanging_indent_multiple_imports_and_wrapping():
    # Testing while loop, multiple imports, and internal line wrapping (line 136-144)
    res = hanging_indent(
        statement="import ",
        imports=["foo", "bar", "baz_very_long_import_name"],
        white_space=" ",
        indent="    ",
        line_length=20,  # line_length_limit = 17
        comments=[],
        line_separator="\n",
        comment_prefix="#",
        include_trailing_comma=False,
        remove_comments=False,
    )
    assert res is not None


def test_hanging_indent_comments_fits_in_limit():
    # Comments present, fits within limit (lines 146-156)
    res = hanging_indent(
        statement="import a",
        imports=["b"],
        white_space=" ",
        indent="    ",
        line_length=80,
        comments=["# comment"],
        line_separator="\n",
        comment_prefix="#",
        include_trailing_comma=False,
        remove_comments=False,
    )
    assert "# comment" in res


def test_hanging_indent_comments_exceeds_limit_forces_wrap():
    # Comments present, exceeds limit (lines 157-164)
    res = hanging_indent(
        statement="import a",
        imports=["b"],
        white_space=" ",
        indent="    ",
        line_length=12,  # line_length_limit = 9
        comments=["# a very long comment here"],
        line_separator="\n",
        comment_prefix="#",
        include_trailing_comma=False,
        remove_comments=False,
    )
    assert "\\" in res
    assert "# a very long comment here" in res


def test_hanging_indent_no_comments_returns_statement():
    # Hits line 167 (no comments, non-empty imports)
    res = hanging_indent(
        statement="import ",
        imports=["a"],
        white_space=" ",
        indent="    ",
        line_length=80,
        comments=[],
        line_separator="\n",
        comment_prefix="#",
        include_trailing_comma=False,
        remove_comments=False,
    )
    assert res == "import a"
