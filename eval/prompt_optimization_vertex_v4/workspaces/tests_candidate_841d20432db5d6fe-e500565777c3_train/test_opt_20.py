# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}

import pytest
from isort.wrap_modes import noqa

def test_noqa_wrap_mode_with_comments_fitting_line_length():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": ["# comment"],
        "comment_prefix": "  #",
        "line_length": 30,
    }
    # retval = "import os" (len 9)
    # comment_str = "# comment" (len 9)
    # len(retval) + len(comment_prefix) + 1 + len(comment_str) = 9 + 3 + 1 + 9 = 22 <= 30
    result = noqa(**interface)
    assert result == "import os  # # comment"

def test_noqa_wrap_mode_with_comments_containing_noqa_exceeding_line_length():
    interface = {
        "statement": "import ",
        "imports": ["os", "sys", "math"],
        "comments": ["NOQA", "extra"],
        "comment_prefix": "  #",
        "line_length": 15,
    }
    # retval exceeds line_length and 'NOQA' is in comments
    result = noqa(**interface)
    assert result == "import os, sys, math  # NOQA extra"

def test_noqa_wrap_mode_with_comments_not_fitting_and_no_noqa():
    interface = {
        "statement": "import ",
        "imports": ["os", "sys", "math"],
        "comments": ["note"],
        "comment_prefix": "  #",
        "line_length": 15,
    }
    # retval exceeds line_length, 'NOQA' not in comments -> adds NOQA
    result = noqa(**interface)
    assert result == "import os, sys, math  # NOQA note"

def test_noqa_wrap_mode_no_comments_fitting_line_length():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": [],
        "comment_prefix": "  #",
        "line_length": 20,
    }
    # retval = "import os" (len 9) <= 20
    result = noqa(**interface)
    assert result == "import os"

def test_noqa_wrap_mode_no_comments_exceeding_line_length():
    interface = {
        "statement": "import ",
        "imports": ["os", "sys", "math"],
        "comments": [],
        "comment_prefix": "  #",
        "line_length": 10,
    }
    # retval exceeds 10 and no comments -> adds NOQA
    result = noqa(**interface)
    assert result == "import os, sys, math  # NOQA"
