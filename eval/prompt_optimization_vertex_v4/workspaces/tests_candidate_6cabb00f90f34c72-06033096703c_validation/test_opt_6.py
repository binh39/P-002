# file: src\sample_repo\isort\isort\parse.py:81-124
# asked: {"lines": [81, 82, 83, 84, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}
# gained: {"lines": [81, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}

from isort.parse import skip_line

def test_skip_line_in_quote_continuation():
    # Test starting with an active quote (in_quote is non-empty), and closing it
    skip, quote = skip_line('some_end_quote"', in_quote='"', index=0, section_comments=())
    assert skip is True
    assert quote == ""

def test_skip_line_escaped_character_and_quotes():
    # Test backslash escape inside quote loop (line 99-100), single quote vs triple quote (lines 105-110), and comment break (lines 111-112).
    line = r'x = "hello \"world\"" # comment'
    skip, quote = skip_line(line, in_quote="", index=0, section_comments=())
    assert skip is False
    assert quote == ""

def test_skip_line_triple_quotes():
    # Test long_quote matching '"""' or "'''" (lines 105-107)
    line = '""" docstring '
    skip, quote = skip_line(line, in_quote="", index=0, section_comments=())
    assert skip is True
    assert quote == '"""'

    # Test closing triple quotes on a subsequent line
    # When in_quote is active, should_skip starts as True (bool(in_quote) is True).
    line2 = 'end """ extra'
    skip, quote = skip_line(line2, in_quote='"""', index=0, section_comments=())
    assert skip is True
    assert quote == ""

def test_skip_line_semicolon_needs_import():
    # Test lines 115-122: ';' in line.split('#')[0] and needs_import
    # Part that does not start with 'from ', 'import ', or 'cimport '
    line = "import os; x = 1"
    skip, quote = skip_line(line, in_quote="", index=0, section_comments=(), needs_import=True)
    assert skip is True
    assert quote == ""

def test_skip_line_semicolon_with_valid_import_parts():
    # Test semicolon parts that are valid imports or empty, so should_skip remains False
    line = "import os; import sys; from math import sin"
    skip, quote = skip_line(line, in_quote="", index=0, section_comments=(), needs_import=True)
    assert skip is False
    assert quote == ""

def test_skip_line_semicolon_needs_import_false():
    # Test needs_import=False so semicolon check is skipped
    line = "import os; x = 1"
    skip, quote = skip_line(line, in_quote="", index=0, section_comments=(), needs_import=False)
    assert skip is False
    assert quote == ""
