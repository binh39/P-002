# file: src\sample_repo\typesystem\typesystem\tokenize\tokens.py:56-61
# asked: {"lines": [56, 57, 58, 59, 60, 61], "branches": []}
# gained: {"lines": [56, 57, 58, 59, 60, 61], "branches": []}

from typesystem.tokenize.tokens import Token
from typesystem.base import Position

def test_token_get_position():
    # Test with content spanning multiple lines and columns
    content = "line1\nline2_ext"
    token = Token(value="test", start_index=0, end_index=len(content) - 1, content=content)
    
    # Position for index 0 ('l' of line1) -> line 1, column 1
    pos_0 = token._get_position(0)
    assert pos_0 == Position(line_no=1, column_no=1, char_index=0)

    # Position for index 4 ('1' of line1) -> line 1, column 5
    pos_4 = token._get_position(4)
    assert pos_4 == Position(line_no=1, column_no=5, char_index=4)

    # Position for index 5 ('\n') -> line 1, column 5 (since splitlines drops trailing newline / empty line for splitlines unless specified, but let's check what it produces: content[:6] is "line1\n", lines is ["line1"], len(lines[-1]) is 5)
    pos_5 = token._get_position(5)
    assert pos_5 == Position(line_no=1, column_no=5, char_index=5)

    # Position for index 6 ('l' of line2_ext) -> line 2, column 1
    pos_6 = token._get_position(6)
    assert pos_6 == Position(line_no=2, column_no=1, char_index=6)

    # Position for index 11 ('e' of line2_ext) -> line 2, column 6
    pos_11 = token._get_position(11)
    assert pos_11 == Position(line_no=2, column_no=6, char_index=11)
