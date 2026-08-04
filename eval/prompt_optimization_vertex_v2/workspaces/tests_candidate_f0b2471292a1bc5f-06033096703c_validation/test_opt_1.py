# file: src\sample_repo\isort\isort\parse.py:81-124
# asked: {"lines": [81, 82, 83, 84, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}
# gained: {"lines": [81, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}

from isort.parse import skip_line

def test_skip_line_already_in_quote():
    # Covers should_skip = True when in_quote is passed
    # Also tests matching closing quote
    res = skip_line('some text "', '"', 0, ())
    assert res == (True, "")

def test_skip_line_escaped_quote():
    # Covers backslash handling: line[char_index] == "\\"
    res = skip_line(r'foo \" bar', '', 0, ())
    assert res == (False, "")

def test_skip_line_triple_quotes():
    # Covers long_quote in ('"""', "'''") and char_index += 2
    res = skip_line('def foo(): """docstring', '', 0, ())
    assert res == (True, '"""')

def test_skip_line_single_quote():
    # Covers single quote opening and # comment break
    res = skip_line("x = 'abc' # comment", '', 0, ())
    assert res == (False, "")

def test_skip_line_semicolon_needs_import():
    # Covers ';' in line.split('#')[0] and needs_import=True with various parts
    # Part 1: 'import os' (starts with 'import ')
    # Part 2: 'x = 1' (should trigger should_skip = True)
    res = skip_line("import os; x = 1", '', 0, (), needs_import=True)
    assert res == (True, "")

def test_skip_line_semicolon_needs_import_false():
    # Covers needs_import=False preventing should_skip even if non-import statement exists after semicolon
    res = skip_line("import os; x = 1", '', 0, (), needs_import=False)
    assert res == (False, "")

def test_skip_line_semicolon_with_comment():
    # Covers split('#')[0] filtering out comments containing ';'
    res = skip_line("import os # comment; x = 1", '', 0, (), needs_import=True)
    assert res == (False, "")

def test_skip_line_semicolon_with_from_and_cimport():
    # Covers parts starting with 'from ' and 'cimport ' not triggering should_skip
    res = skip_line("from a import b; cimport d", '', 0, (), needs_import=True)
    assert res == (False, "")
