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
    """Fixture to mock the parse function."""
    monkeypatch.setattr("isort.comments.parse", mock_parse)

def test_add_to_line_with_removed(mock_parse_function):
    """Test the case where removed is True."""
    result = add_to_line(comments=["This is a comment"], original_string="Original string", removed=True)
    assert result == "Original string"

def test_add_to_line_with_no_comments(mock_parse_function):
    """Test the case where comments is None."""
    result = add_to_line(comments=None, original_string="Original string")
    assert result == "Original string"

def test_add_to_line_with_empty_comments(mock_parse_function):
    """Test the case where comments is an empty list."""
    result = add_to_line(comments=[], original_string="Original string")
    assert result == "Original string"

def test_add_to_line_with_unique_comments(mock_parse_function):
    """Test the case where unique comments are added."""
    comments = ["Comment 1", "Comment 2", "Comment 1"]
    result = add_to_line(comments=comments, original_string="Original string")
    assert result == "Original string Comment 1; Comment 2"

