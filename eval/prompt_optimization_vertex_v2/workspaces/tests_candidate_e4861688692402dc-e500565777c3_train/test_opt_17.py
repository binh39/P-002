# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}

import pytest
from isort.wrap_modes import noqa

def test_noqa_with_comments_fitting_line_length():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": ["comment1"],
        "comment_prefix": "  #",
        "line_length": 30,
    }
    # len(retval) = len("import os") = 9
    # len("  #") = 3
    # len(" ") = 1
    # len("comment1") = 8
    # Total = 9 + 3 + 1 + 8 = 21 <= 30
    result = noqa(**interface)
    assert result == "import os  # comment1"

def test_noqa_with_comments_exceeding_line_length_but_has_noqa():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": ["NOQA", "comment1"],
        "comment_prefix": "  #",
        "line_length": 15,
    }
    # Total length exceeds 15, but "NOQA" is in interface["comments"]
    result = noqa(**interface)
    assert result == "import os  # NOQA comment1"

def test_noqa_with_comments_exceeding_line_length_no_noqa():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": ["comment1"],
        "comment_prefix": "  #",
        "line_length": 15,
    }
    # Total length exceeds 15, "NOQA" not in interface["comments"]
    result = noqa(**interface)
    assert result == "import os  # NOQA comment1"

def test_noqa_without_comments_fitting_line_length():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": [],
        "comment_prefix": "  #",
        "line_length": 15,
    }
    # len(retval) = 9 <= 15
    result = noqa(**interface)
    assert result == "import os"

def test_noqa_without_comments_exceeding_line_length():
    interface = {
        "statement": "import ",
        "imports": ["very_long_module_name"],
        "comments": [],
        "comment_prefix": "  #",
        "line_length": 10,
    }
    # len(retval) = len("import very_long_module_name") > 10
    result = noqa(**interface)
    assert result == "import very_long_module_name  # NOQA"
