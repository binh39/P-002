# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}

from isort.wrap_modes import noqa

def test_noqa_wrap_mode_with_comments_short_line():
    interface = {
        "statement": "import ",
        "imports": ["os", "sys"],
        "comments": ["# comment"],
        "comment_prefix": " #",
        "line_length": 50,
    }
    # retval = "import os, sys" (len 14)
    # comment_str = "# comment" (len 9)
    # len(retval) + len(comment_prefix) + 1 + len(comment_str) = 14 + 2 + 1 + 9 = 26 <= 50
    result = noqa(**interface)
    assert result == "import os, sys # # comment"

def test_noqa_wrap_mode_with_comments_noqa_present():
    interface = {
        "statement": "import ",
        "imports": ["a" * 40],
        "comments": ["NOQA"],
        "comment_prefix": " #",
        "line_length": 20,
    }
    # Exceeds line length, but "NOQA" in interface["comments"]
    result = noqa(**interface)
    assert result == f"import {'a' * 40} # NOQA"

def test_noqa_wrap_mode_with_comments_noqa_absent_long_line():
    interface = {
        "statement": "import ",
        "imports": ["a" * 40],
        "comments": ["custom"],
        "comment_prefix": " #",
        "line_length": 20,
    }
    # Exceeds line length, "NOQA" not in comments -> inserts NOQA
    result = noqa(**interface)
    assert result == f"import {'a' * 40} # NOQA custom"

def test_noqa_wrap_mode_no_comments_short_line():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 20,
    }
    # retval = "import os" (len 9) <= 20
    result = noqa(**interface)
    assert result == "import os"

def test_noqa_wrap_mode_no_comments_long_line():
    interface = {
        "statement": "import ",
        "imports": ["a" * 30],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 20,
    }
    # retval = "import " + "a"*30 (len 37) > 20, no comments
    result = noqa(**interface)
    assert result == f"import {'a' * 30} # NOQA"
