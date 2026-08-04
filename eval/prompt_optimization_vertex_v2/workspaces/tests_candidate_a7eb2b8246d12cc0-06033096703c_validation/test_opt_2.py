# file: src\sample_repo\isort\isort\parse.py:81-124
# asked: {"lines": [81, 82, 83, 84, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}
# gained: {"lines": [81, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}

from isort.parse import skip_line


def test_skip_line_in_quote_continuation():
    # Test when already inside a quote, and the quote ends on this line
    skip, quote = skip_line('end_quote"', '"', 0, ())
    # Since should_skip = bool(in_quote) is True at start, should_skip remains True
    assert skip is True
    assert quote == ""


def test_skip_line_escaped_character():
    # Test when there is an escaped character inside quotes or normal text
    skip, quote = skip_line(r'x = "abc\"def"', "", 0, ())
    assert skip is False
    assert quote == ""


def test_skip_line_triple_quotes():
    # Test entering triple quotes
    skip, quote = skip_line('"""start triple', "", 0, ())
    assert skip is True
    assert quote == '"""'

    # Test exiting triple quotes where the line still starts in_quote ('"""'), 
    # so should_skip starts True and remains True because of bool(in_quote) or the closing quote.
    skip, quote = skip_line('end triple"""', '"""', 0, ())
    assert skip is True
    assert quote == ""


def test_skip_line_single_quote_char():
    # Test single quote inside line with comment after
    skip, quote = skip_line("x = 'a' # comment", "", 0, ())
    assert skip is False
    assert quote == ""


def test_skip_line_hash_outside_quotes():
    # Test hitting a hash symbol outside quotes (breaking out of character loop)
    skip, quote = skip_line("x = 1 # quote'", "", 0, ())
    assert skip is False
    assert quote == ""


def test_skip_line_semicolon_needs_import_true_non_import():
    # Test semicolon with needs_import=True and a statement that is not an import
    skip, quote = skip_line("x = 1; y = 2", "", 0, ())
    assert skip is True
    assert quote == ""


def test_skip_line_semicolon_needs_import_false():
    # Test semicolon with needs_import=False (should not skip even if non-import)
    skip, quote = skip_line("x = 1; y = 2", "", 0, (), needs_import=False)
    assert skip is False
    assert quote == ""


def test_skip_line_semicolon_with_import_statements():
    # Test semicolon containing valid import parts and needs_import=True
    skip, quote = skip_line("import os; import sys", "", 0, ())
    assert skip is False
    assert quote == ""
