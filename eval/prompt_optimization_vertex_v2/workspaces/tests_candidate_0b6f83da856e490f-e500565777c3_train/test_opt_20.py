# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}

from typing import Any
from isort.wrap_modes import noqa, formatter_from_string

def test_noqa_wrap_mode_with_comments_short() -> None:
    # Test lines 248-253: comments present and total length <= line_length
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": ["# comment"],
        "comment_prefix": "  #",
        "line_length": 30,
        "white_space": "",
        "indent": "",
        "line_separator": "\n",
        "include_trailing_comma": False,
        "remove_comments": False,
    }
    result = noqa(**interface)
    assert result == "import os  # # comment"

def test_noqa_wrap_mode_with_comments_noqa_in_comments() -> None:
    # Test lines 254-255: comments present, length > line_length, but "NOQA" in comments
    interface = {
        "statement": "import ",
        "imports": ["os, sys, math, subprocess"],
        "comments": ["NOQA"],
        "comment_prefix": "  #",
        "line_length": 20,
        "white_space": "",
        "indent": "",
        "line_separator": "\n",
        "include_trailing_comma": False,
        "remove_comments": False,
    }
    result = noqa(**interface)
    assert result == "import os, sys, math, subprocess  # NOQA"

def test_noqa_wrap_mode_with_comments_adds_noqa() -> None:
    # Test line 256: comments present, length > line_length, and "NOQA" not in comments
    interface = {
        "statement": "import ",
        "imports": ["os, sys, math, subprocess"],
        "comments": ["custom"],
        "comment_prefix": "  #",
        "line_length": 20,
        "white_space": "",
        "indent": "",
        "line_separator": "\n",
        "include_trailing_comma": False,
        "remove_comments": False,
    }
    result = noqa(**interface)
    assert result == "import os, sys, math, subprocess  # NOQA custom"

def test_noqa_wrap_mode_no_comments_short() -> None:
    # Test lines 258-259: no comments, retval length <= line_length
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": [],
        "comment_prefix": "  #",
        "line_length": 30,
        "white_space": "",
        "indent": "",
        "line_separator": "\n",
        "include_trailing_comma": False,
        "remove_comments": False,
    }
    result = noqa(**interface)
    assert result == "import os"

def test_noqa_wrap_mode_no_comments_long() -> None:
    # Test line 260: no comments, retval length > line_length
    interface = {
        "statement": "import ",
        "imports": ["os, sys, math, subprocess"],
        "comments": [],
        "comment_prefix": "  #",
        "line_length": 20,
        "white_space": "",
        "indent": "",
        "line_separator": "\n",
        "include_trailing_comma": False,
        "remove_comments": False,
    }
    result = noqa(**interface)
    assert result == "import os, sys, math, subprocess  # NOQA"

def test_formatter_from_string_noqa() -> None:
    formatter = formatter_from_string("NOQA")
    assert callable(formatter)
