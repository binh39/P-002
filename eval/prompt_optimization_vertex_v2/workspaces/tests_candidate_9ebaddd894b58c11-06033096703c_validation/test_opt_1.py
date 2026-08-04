# file: src\sample_repo\isort\isort\parse.py:81-124
# asked: {"lines": [81, 82, 83, 84, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}
# gained: {"lines": [81, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}

from isort.parse import skip_line

def test_skip_line_already_in_quote_and_closing():
    # Covers: in_quote is truthy initially, hits line[char_index] == '\\',
    # and matches closing quote. Also tests when quote closes.
    # line with escaped char inside quote: 'a\"b'
    res, quote = skip_line(r'a\"b"', in_quote='"', index=0, section_comments=())
    assert quote == ""

def test_skip_line_triple_quotes():
    # Covers: long_quote in ('"""', "'''") branch (lines 106-107) and char_index += 2 (line 108)
    res, quote = skip_line('"""docstring', in_quote="", index=0, section_comments=())
    assert quote == '"""'

    # Covers closing triple quote
    res, quote = skip_line('end"""', in_quote='"""', index=0, section_comments=())
    assert quote == ""

def test_skip_line_single_quote_and_comment_break():
    # Covers single quote else branch (line 110) and '#' break branch (lines 111-112)
    res, quote = skip_line("x = 'a' # comment", in_quote="", index=0, section_comments=())
    assert quote == ""
    assert res is False

def test_skip_line_semicolon_needs_import_various_parts():
    # Covers: ';' in line.split("#")[0] and needs_import
    # Parts that trigger should_skip = True (lines 116-122)
    # Part 1: empty/whitespace (part falsy)
    # Part 2: starts with 'from ' (skipped)
    # Part 3: starts with 'import ' (skipped)
    # Part 4: random statement like 'x = 1' (should_skip = True)
    line = "from a import b; import c; x = 1; "
    res, quote = skip_line(line, in_quote="", index=0, section_comments=(), needs_import=True)
    assert res is True

    # Part starting with cimport
    line2 = "cimport b; y = 2"
    res2, quote2 = skip_line(line2, in_quote="", index=0, section_comments=(), needs_import=True)
    assert res2 is True

def test_skip_line_semicolon_needs_import_false():
    # Covers needs_import=False branch
    line = "x = 1; y = 2"
    res, quote = skip_line(line, in_quote="", index=0, section_comments=(), needs_import=False)
    assert res is False

def test_skip_line_in_quote_at_end():
    # Covers should_skip or in_quote being true at return (line 124) due to unclosed quote
    res, quote = skip_line("print('hello", in_quote="", index=0, section_comments=())
    assert res is True
    assert quote == "'"
