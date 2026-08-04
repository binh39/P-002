# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}

import pytest
from isort.wrap_modes import noqa

def test_noqa_with_comments_fits_line():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": ["# comment"],
        "comment_prefix": "  #",
        "line_length": 50,
    }
    result = noqa(**interface)
    # len(retval) = len("import os") = 9
    # len(comment_prefix) = 3 ("  #")
    # len(comment_str) = 9 ("# comment")
    # total length = 9 + 3 + 1 + 9 = 22 <= 50
    assert result == "import os  # # comment"

def test_noqa_with_comments_exceeds_line_but_has_noqa():
    interface = {
        "statement": "import ",
        "imports": ["very_long_module_name_to_exceed_length"],
        "comments": ["NOQA"],
        "comment_prefix": "  #",
        "line_length": 20,
    }
    result = noqa(**interface)
    # Exceeds line length, but "NOQA" is in comments
    assert result == "import very_long_module_name_to_exceed_length  # NOQA"

def test_noqa_with_comments_exceeds_line_no_noqa():
    interface = {
        "statement": "import ",
        "imports": ["very_long_module_name_to_exceed_length"],
        "comments": ["# comment"],
        "comment_prefix": "  #",
        "line_length": 20,
    }
    result = noqa(**interface)
    # Exceeds line length, "NOQA" not in comments -> inserts NOQA
    assert result == "import very_long_module_name_to_exceed_length  # NOQA # comment"

def test_noqa_no_comments_fits_line():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": [],
        "comment_prefix": "  #",
        "line_length": 50,
    }
    result = noqa(**interface)
    # No comments, retval fits within line_length
    assert result == "import os"

def test_noqa_no_comments_exceeds_line():
    interface = {
        "statement": "import ",
        "imports": ["very_long_module_name_to_exceed_length"],
        "comments": [],
        "comment_prefix": "  #",
        "line_length": 20,
    }
    result = noqa(**interface)
    # No comments, retval exceeds line_length -> appends comment_prefix + NOQA
    assert result == "import very_long_module_name_to_exceed_length  # NOQA"
