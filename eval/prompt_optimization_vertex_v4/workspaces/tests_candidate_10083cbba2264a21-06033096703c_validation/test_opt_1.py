# file: src\sample_repo\isort\isort\parse.py:81-124
# asked: {"lines": [81, 82, 83, 84, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}
# gained: {"lines": [81, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 113, 115, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 113], [115, 124]]}

from isort.parse import skip_line

def test_skip_line_in_quote_continuation():
    # Test starting inside a quote and closing it, with escape characters and regular chars
    # line: r'text" closing quote'
    # in_quote: '"'
    # Should execute lines 95-113 with in_quote true, handling escape '\\', closing quote, etc.
    line = r'foo\"bar" baz'
    # start with in_quote = '"'
    skip, quote = skip_line(line, in_quote='"', index=0, section_comments=())
    assert not quote

def test_skip_line_open_quotes():
    # Test opening single, double, and triple quotes (both long quote branches: long_quote in ('"""', "'''") True and False)
    # Single quote opening
    line_single = "x = 'hello'"
    skip, quote = skip_line(line_single, in_quote="", index=0, section_comments=())
    assert not quote

    # Triple double quote opening
    line_triple = 'x = """hello"""'
    skip, quote = skip_line(line_triple, in_quote="", index=0, section_comments=())
    assert not quote

    # Hash inside quote should be ignored
    line_hash_in_quote = 'x = "hello # world"'
    skip, quote = skip_line(line_hash_in_quote, in_quote="", index=0, section_comments=())
    assert not quote

    # Hash outside quote should break
    line_hash_outside = 'x = 1 # comment'
    skip, quote = skip_line(line_hash_outside, in_quote="", index=0, section_comments=())
    assert not skip

def tf_skip_line_semicolon_needs_import():
    # Test semicolon branch (lines 115-122)
    # needs_import = True, semicolon present, parts that do not start with from/import/cimport
    line = "import os; x = 1"
    skip, quote = skip_line(line, in_quote="", index=0, section_comments=(), needs_import=True)
    assert skip

    # Part is empty or starts with import/from
    line_valid = "import os; import sys"
    skip, quote = skip_line(line_valid, in_quote="", index=0, section_comments=(), needs_import=True)
    assert not skip

    # needs_import = False
    skip, quote = skip_line(line, in_quote="", index=0, section_comments=(), needs_import=False)
    assert not skip

    # Semicolon inside comment part should be ignored by split('#')[0]
    line_comment_semi = "import os # comment; x = 1"
    skip, quote = skip_line(line_comment_semi, in_quote="", index=0, section_comments=(), needs_import=True)
    assert not skip
