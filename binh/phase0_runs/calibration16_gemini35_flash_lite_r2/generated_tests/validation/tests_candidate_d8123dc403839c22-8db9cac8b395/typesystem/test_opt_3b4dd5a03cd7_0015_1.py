# file: src\sample_repo\typesystem\typesystem\tokenize\tokens.py:56-61
# asked: {"lines": [56, 57, 58, 59, 60, 61], "branches": []}
# gained: {"lines": [56, 57, 58, 59, 60, 61], "branches": []}

from typesystem.tokenize.tokens import Token
from typesystem.base import Position

def test_token_get_position():
    # Test with multi-line content
    content = "hello\nworld"
    token = Token(value="test", start_index=0, end_index=len(content) - 1, content=content)
    
    # Index pointing to 'h' in "hello" (line 1, col 1)
    pos_0 = token._get_position(0)
    assert pos_0 == Position(line_no=1, column_no=1, char_index=0)
    
    # Index pointing to '\n' (line 1, col 5)
    pos_5 = token._get_position(5)
    assert pos_5 == Position(line_no=1, column_no=5, char_index=5)

    # Index pointing to 'w' in "world" (line 2, col 1)
    pos_6 = token._get_position(6)
    assert pos_6 == Position(line_no=2, column_no=1, char_index=6)

    # Test with empty content to cover branch where lines is empty
    empty_token = Token(value="test", start_index=0, end_index=0, content="")
    pos_empty = empty_token._get_position(0)
    assert pos_empty == Position(line_no=1, column_no=1, char_index=0)
