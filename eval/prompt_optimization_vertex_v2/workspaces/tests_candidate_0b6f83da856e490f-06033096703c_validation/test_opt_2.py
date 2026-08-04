# file: src\sample_repo\isort\isort\parse.py:81-124
# asked: {"lines": [81, 82, 83, 84, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}
# gained: {"lines": [81, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}

import pytest
from isort.parse import skip_line

def test_skip_line_all_branches():
    # 1. Test already in_quote, escaping backslash, closing quote
    # and line with single quote starting and ending quote matching in_quote
    skip, quote = skip_line(r'some \' string ending "', '"""', 0, (), True)
    assert skip is True
    assert quote == '"""'

    # Close quote case (when in_quote is active, returns in_quote which makes bool(should_skip or in_quote) True)
    skip, quote = skip_line('still in quote"', '"', 0, (), True)
    assert skip is True
    assert quote == ''

    # 2. Test opening triple quote vs single quote
    # Triple quote open
    skip, quote = skip_line('x = """hello', '', 0, (), True)
    assert skip is True
    assert quote == '"""'

    # Single quote open
    skip, quote = skip_line("x = 'hello", '', 0, (), True)
    assert skip is True
    assert quote == "'"

    # 3. Test encountering comment '#' after quote/code
    skip, quote = skip_line("x = 1 # comment with 'quote", '', 0, (), True)
    assert skip is False
    assert quote == ''

    # 4. Test semicolon parsing (lines 115-122)
    # needs_import = True, semicolon present, but parts are imports or empty
    skip, quote = skip_line("import os; import sys;", '', 0, (), True)
    assert skip is False

    # needs_import = True, semicolon present, with a non-import part (should set should_skip = True)
    skip, quote = skip_line("import os; x = 1", '', 0, (), True)
    assert skip is True

    # needs_import = False, semicolon present with non-import part (should not set should_skip)
    skip, quote = skip_line("import os; x = 1", '', 0, (), False)
    assert skip is False

    # part starting with 'from ' or 'import ' or 'cimport '
    skip, quote = skip_line("x = 1; from a import b", '', 0, (), True)
    assert skip is True  # 'x = 1' is non-import part

    skip, quote = skip_line("cimport foo; import bar", '', 0, (), True)
    assert skip is False
