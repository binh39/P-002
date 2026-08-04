# file: src\sample_repo\isort\isort\parse.py:81-124
# asked: {"lines": [81, 82, 83, 84, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}
# gained: {"lines": [81, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}

from isort.parse import skip_line


def test_skip_line_basic_quotes_and_comments():
    # Test entering a single quote
    skip, in_quote = skip_line("x = 'hello", "", 0, ())
    assert skip is True
    assert in_quote == "'"

    # Test closing an existing single quote
    skip, in_quote = skip_line("world'", "'", 0, ())
    assert skip is True
    assert in_quote == ""

    # Test long quotes (triple quotes)
    skip, in_quote = skip_line('x = """hello', "", 0, ())
    assert skip is True
    assert in_quote == '"""'

    # Test closing long quotes
    skip, in_quote = skip_line('world"""', '"""', 0, ())
    assert skip is True
    assert in_quote == ""

    # Test escaped quote and comment break
    skip, in_quote = skip_line(r'print("hello \" world") # comment', "", 0, ())
    assert skip is False
    assert in_quote == ""


def test_skip_line_semicolon_statements():
    # Semicolon statement that is an import -> should not skip
    skip, in_quote = skip_line("import os; import sys", "", 0, (), needs_import=True)
    assert skip is False

    # Semicolon statement with 'from' -> should not skip
    skip, in_quote = skip_line("from os import path; import sys", "", 0, (), needs_import=True)
    assert skip is False

    # Semicolon statement with 'cimport' -> should not skip
    skip, in_quote = skip_line("cimport module; import sys", "", 0, (), needs_import=True)
    assert skip is False

    # Semicolon statement that is not an import -> should skip
    skip, in_quote = skip_line("x = 1; import sys", "", 0, (), needs_import=True)
    assert skip is True

    # Semicolon statement when needs_import is False -> should not skip
    skip, in_quote = skip_line("x = 1; import sys", "", 0, (), needs_import=False)
    assert skip is False

    # Semicolon inside a comment before the actual semicolon -> should not skip
    skip, in_quote = skip_line("import sys # comment; x = 1", "", 0, (), needs_import=True)
    assert skip is False
