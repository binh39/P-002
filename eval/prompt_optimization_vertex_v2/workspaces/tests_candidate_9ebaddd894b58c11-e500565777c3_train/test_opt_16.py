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
        "comment_prefix": " #",
        "line_length": 30,
    }
    result = noqa(**interface)
    assert result == "import os # comment1"

def test_noqa_with_comments_not_fitting_but_has_noqa():
    interface = {
        "statement": "import ",
        "imports": ["os", "sys"],
        "comments": ["NOQA"],
        "comment_prefix": " #",
        "line_length": 10,
    }
    result = noqa(**interface)
    assert result == "import os, sys # NOQA"

def test_noqa_with_comments_not_fitting_and_no_noqa():
    interface = {
        "statement": "import ",
        "imports": ["os", "sys"],
        "comments": ["comment1"],
        "comment_prefix": " #",
        "line_length": 10,
    }
    result = noqa(**interface)
    assert result == "import os, sys # NOQA comment1"

def test_noqa_without_comments_fitting_line_length():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 20,
    }
    result = noqa(**interface)
    assert result == "import os"

def test_noqa_without_comments_exceeding_line_length():
    interface = {
        "statement": "import ",
        "imports": ["os", "sys", "math", "itertools"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 10,
    }
    result = noqa(**interface)
    assert result == "import os, sys, math, itertools # NOQA"
