# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}

from isort.wrap_modes import noqa

def test_noqa_wrap_mode_with_comments_short_line():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": ["# comment"],
        "comment_prefix": "  #",
        "line_length": 50,
    }
    # len(retval) = len("import os") = 9
    # len(comment_prefix) = 3 ("  #")
    # len(comment_str) = 9 ("# comment")
    # total length = 9 + 3 + 1 + 9 = 22 <= 50 (line_length)
    result = noqa(**interface)
    assert result == "import os  # # comment"

def test_noqa_wrap_mode_with_comments_noqa_in_comments():
    interface = {
        "statement": "import ",
        "imports": ["os", "sys", "subprocess", "shutil"],
        "comments": ["NOQA"],
        "comment_prefix": "  #",
        "line_length": 20,
    }
    # Exceeds line length, but "NOQA" is in comments
    result = noqa(**interface)
    assert result == "import os, sys, subprocess, shutil  # NOQA"

def test_noqa_wrap_mode_with_comments_noqa_not_in_comments():
    interface = {
        "statement": "import ",
        "imports": ["os", "sys", "subprocess", "shutil"],
        "comments": ["custom_comment"],
        "comment_prefix": "  #",
        "line_length": 20,
    }
    # Exceeds line length, and "NOQA" not in comments -> inserts NOQA
    result = noqa(**interface)
    assert result == "import os, sys, subprocess, shutil  # NOQA custom_comment"

def test_noqa_wrap_mode_without_comments_short_line():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": [],
        "comment_prefix": "  #",
        "line_length": 20,
    }
    # No comments, retval length <= line_length
    result = noqa(**interface)
    assert result == "import os"

def test_noqa_wrap_mode_without_comments_long_line():
    interface = {
        "statement": "import ",
        "imports": ["os", "sys", "subprocess"],
        "comments": [],
        "comment_prefix": "  #",
        "line_length": 10,
    }
    # No comments, retval length > line_length -> appends NOQA
    result = noqa(**interface)
    assert result == "import os, sys, subprocess  # NOQA"
