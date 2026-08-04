# file: src\sample_repo\isort\isort\parse.py:81-124
# asked: {"lines": [81, 82, 83, 84, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}
# gained: {"lines": [81, 85, 86, 87, 95, 96, 97, 98, 99, 101, 102, 103, 104, 105, 106, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}

import pytest
from isort.parse import skip_line




def test_skip_line_with_comment():
    line = 'print("Hello, World!") # This is a comment'
    in_quote = ''
    index = 0
    section_comments = ()
    needs_import = True
    result = skip_line(line, in_quote, index, section_comments, needs_import)
    assert result == (False, '')

def test_skip_line_with_semicolon_and_import():
    line = 'x = 1; import os'
    in_quote = ''
    index = 0
    section_comments = ()
    needs_import = True
    result = skip_line(line, in_quote, index, section_comments, needs_import)
    assert result == (True, '')

def test_skip_line_with_semicolon_without_import():
    line = 'x = 1; y = 2'
    in_quote = ''
    index = 0
    section_comments = ()
    needs_import = True
    result = skip_line(line, in_quote, index, section_comments, needs_import)
    assert result == (True, '')

def test_skip_line_no_skip():
    line = 'import os'
    in_quote = ''
    index = 0
    section_comments = ()
    needs_import = True
    result = skip_line(line, in_quote, index, section_comments, needs_import)
    assert result == (False, '')

def test_skip_line_no_needs_import():
    line = 'x = 1; y = 2'
    in_quote = ''
    index = 0
    section_comments = ()
    needs_import = False
    result = skip_line(line, in_quote, index, section_comments, needs_import)
    assert result == (False, '')
