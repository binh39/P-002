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
    # retval = "import os, sys", len = 14
    # comment_str = "# comment", len = 9
    # comment_prefix = " #", len = 2
    # 14 + 2 + 1 + 9 = 26 <= 50 -> returns retval + comment_prefix + " " + comment_str
    result = noqa(**interface)
    assert result == "import os, sys # # comment"

def test_noqa_wrap_mode_with_comments_noqa_in_comments():
    interface = {
        "statement": "import " + "a" * 40,
        "imports": ["b"],
        "comments": ["NOQA"],
        "comment_prefix": " #",
        "line_length": 20,
    }
    # retval is very long, so len(retval) + ... > line_length
    # but "NOQA" in interface["comments"] is True -> returns retval + comment_prefix + " " + comment_str
    result = noqa(**interface)
    assert "NOQA" in result

def test_noqa_wrap_mode_with_comments_long_line_no_noqa():
    interface = {
        "statement": "import " + "a" * 40,
        "imports": ["b"],
        "comments": ["custom"],
        "comment_prefix": " #",
        "line_length": 20,
    }
    # retval is long, "NOQA" not in comments -> returns retval + comment_prefix + " NOQA " + comment_str
    result = noqa(**interface)
    assert "NOQA" in result
    assert "custom" in result

def test_noqa_wrap_mode_no_comments_short_line():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 50,
    }
    # interface["comments"] is empty
    # len(retval) = 10 <= line_length (50) -> returns retval
    result = noqa(**interface)
    assert result == "import os"

def test_noqa_wrap_mode_no_comments_long_line():
    interface = {
        "statement": "import " + "a" * 40,
        "imports": ["b"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 20,
    }
    # interface["comments"] is empty
    # len(retval) > line_length (20) -> returns retval + comment_prefix + " NOQA"
    result = noqa(**interface)
    assert result.endswith(" # NOQA")
