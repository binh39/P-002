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
    # retval = "import os" (len 9)
    # comment_str = "# comment" (len 9)
    # len(retval) + len(comment_prefix) + 1 + len(comment_str) = 9 + 3 + 1 + 9 = 22 <= 50
    result = noqa(**interface)
    assert result == "import os  # # comment"


def test_noqa_with_comments_has_noqa_in_comments():
    interface = {
        "statement": "import " + "a" * 40,
        "imports": ["os"],
        "comments": ["NOQA"],
        "comment_prefix": "  #",
        "line_length": 30,
    }
    # Exceeds line length, but "NOQA" is in interface["comments"]
    result = noqa(**interface)
    assert result == f"{interface['statement']}os  # NOQA"


def test_noqa_with_comments_does_not_fit_and_no_noqa():
    interface = {
        "statement": "import " + "a" * 40,
        "imports": ["os"],
        "comments": ["custom_comment"],
        "comment_prefix": "  #",
        "line_length": 30,
    }
    # Exceeds line length, "NOQA" not in interface["comments"] -> inserts "NOQA"
    result = noqa(**interface)
    assert result == f"{interface['statement']}os  # NOQA custom_comment"


def test_noqa_without_comments_fits_line():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": [],
        "comment_prefix": "  #",
        "line_length": 50,
    }
    # retval = "import os", len 9 <= 50
    result = noqa(**interface)
    assert result == "import os"


def test_noqa_without_comments_exceeds_line():
    interface = {
        "statement": "import " + "a" * 40,
        "imports": ["os"],
        "comments": [],
        "comment_prefix": "  #",
        "line_length": 30,
    }
    # retval exceeds line length, no comments -> appends " NOQA"
    result = noqa(**interface)
    assert result == f"{interface['statement']}os  # NOQA"
