# file: src\sample_repo\isort\isort\parse.py:81-124
# asked: {"lines": [81, 82, 83, 84, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}
# gained: {"lines": [81, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}

from isort.parse import skip_line


def test_skip_line_in_quote_continuation():
    # Test entering a quote, encountering a backslash escape, and closing the quote
    # Covers: in_quote is set, backslash handling (line 99-100), and quote closing (line 102-103)
    line = r"text \' ending"
    # Start with an open quote
    res, quote = skip_line(line, in_quote="'", index=0, section_comments=())
    assert res is True
    assert quote == "'"

    # When line starts with in_quote already active (should_skip = True initially),
    # even if the quote is closed on this line, should_skip is True because should_skip 
    # starts as bool(in_quote) (True) and doesn't get reset to False when in_quote becomes empty.
    line2 = "a' rest"
    res2, quote2 = skip_line(line2, in_quote="'", index=0, section_comments=())
    assert res2 is True
    assert quote2 == ""


def test_skip_line_triple_quotes():
    # Test opening triple quotes. Note that when '"""' starts, in_quote becomes '"""'
    # and the loop consumes the 3 chars, returning should_skip=True (since in_quote is truthy).
    line = '""" docstring start'
    res, quote = skip_line(line, in_quote="", index=0, section_comments=())
    assert res is True
    assert quote == '"""'

    # Close triple quote: line starts with in_quote open, so should_skip starts as True.
    line2 = 'end """'
    res2, quote2 = skip_line(line2, in_quote='"""', index=0, section_comments=())
    assert res2 is True
    assert quote2 == ""


def test_skip_line_single_quote_and_comment_break():
    # Test single quote opening (line 110) and comment break (lines 111-112)
    line = "x = 'hello' # comment"
    res, quote = skip_line(line, in_quote="", index=0, section_comments=())
    assert res is False
    assert quote == ""


def test_skip_line_semicolon_statements():
    # Test semicolon parsing and needs_import logic (lines 115-122)
    # 1. Statement that should cause should_skip = True (not import/from/cimport)
    line1 = "import os; x = 1"
    res1, quote1 = skip_line(line1, in_quote="", index=0, section_comments=(), needs_import=True)
    assert res1 is True

    # 2. Statement with semicolon but needs_import=False
    line2 = "import os; x = 1"
    res2, quote2 = skip_line(line2, in_quote="", index=0, section_comments=(), needs_import=False)
    assert res2 is False

    # 3. Semicolon with valid import part
    line3 = "import os; import sys"
    res3, quote3 = skip_line(line3, in_quote="", index=0, section_comments=(), needs_import=True)
    assert res3 is False

    # 4. Semicolon with from part
    line4 = "import os; from sys import path"
    res4, quote4 = skip_line(line4, in_quote="", index=0, section_comments=(), needs_import=True)
    assert res4 is False

    # 5. Semicolon with cimport part
    line5 = "import os; cimport math"
    res5, quote5 = skip_line(line5, in_quote="", index=0, section_comments=(), needs_import=True)
    assert res5 is False

    # 6. Semicolon inside a comment part (split('#')[0] check)
    line6 = "import os # comment; x = 1"
    res6, quote6 = skip_line(line6, in_quote="", index=0, section_comments=(), needs_import=True)
    assert res6 is False
