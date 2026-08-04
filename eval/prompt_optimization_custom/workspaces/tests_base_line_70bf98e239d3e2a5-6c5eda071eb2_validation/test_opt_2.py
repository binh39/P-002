# file: src\sample_repo\isort\isort\comments.py:12-29
# asked: {"lines": [12, 13, 14, 15, 16, 17, 19, 20, 22, 23, 25, 26, 27, 28, 29], "branches": [[19, 20], [19, 22], [22, 23], [22, 25], [26, 27], [26, 29], [27, 26], [27, 28]]}
# gained: {"lines": [12, 13, 14, 15, 16, 19, 20, 22, 23, 25, 26, 27, 28, 29], "branches": [[19, 20], [19, 22], [22, 23], [22, 25], [26, 27], [26, 29], [27, 26], [27, 28]]}

import pytest
from isort.comments import add_to_line

# Mocking the parse function for testing purposes
def mock_parse(original_string):
    return [original_string]

@pytest.fixture
def mock_parse_function(monkeypatch):
    monkeypatch.setattr("isort.comments.parse", mock_parse)

def test_add_to_line_with_removed(mock_parse_function):
    result = add_to_line(comments=["This is a comment"], original_string="Original string", removed=True)
    assert result == "Original string"  # Should return the original string without comments

def test_add_to_line_with_no_comments(mock_parse_function):
    result = add_to_line(comments=[], original_string="Original string", removed=False)
    assert result == "Original string"  # Should return the original string without comments

def test_add_to_line_with_unique_comments(mock_parse_function):
    comments = ["Comment 1", "Comment 2", "Comment 1"]  # Duplicate comment
    result = add_to_line(comments=comments, original_string="Original string", removed=False, comment_prefix="#")
    assert result == "Original string# Comment 1; Comment 2"  # Should return original string with unique comments

def test_add_to_line_with_none_comments(mock_parse_function):
    result = add_to_line(comments=None, original_string="Original string", removed=False)
    assert result == "Original string"  # Should return the original string without comments
