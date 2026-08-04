# file: src\sample_repo\isort\isort\parse.py:81-124
# asked: {"lines": [81, 82, 83, 84, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}
# gained: {"lines": [81, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}

from isort.parse import skip_line


def test_skip_line_basic_quotes_and_escapes():
    # 1. Test already in_quote and escaping backslash inside quote
    # in_quote = '"', line contains escaped quote and closing quote
    skip, quote = skip_line(r'some \" text"', '"', 0, ())
    assert quote == ""

    # 2. Test triple quotes opening and closing
    skip, quote = skip_line('"""hello', "", 0, ())
    assert quote == '"""'

    # 3. Test single/double quote opening, hashtag comment break, and no quotes/comments
    skip, quote = skip_line("x = 'abc' # comment", "", 0, ())
    assert quote == ""

    # 4. Test hashtag encountered before quotes (or line without quotes)
    skip, quote = skip_line("x = 1 # 'quote'", "", 0, ())
    assert quote == ""

    # 5. Test semicolon splitting with needs_import=True and non-import part
    skip, quote = skip_line("import os; x = 1", "", 0, (), needs_import=True)
    assert skip is True

    # 6. Test semicolon with valid imports and needs_import=False or valid import parts
    skip, quote = skip_line("import os; import sys", "", 0, (), needs_import=True)
    assert skip is False

    skip, quote = skip_line("import os; x = 1", "", 0, (), needs_import=False)
    assert skip is False
