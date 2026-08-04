# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}

import pytest
from isort.wrap_modes import noqa


def test_noqa_wrap_mode_with_comments_fits_line():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": ["comment1"],
        "comment_prefix": " #",
        "line_length": 30,
    }
    result = noqa(**interface)
    assert result == "import os # comment1"


def test_noqa_wrap_mode_with_noqa_in_comments():
    interface = {
        "statement": "import ",
        "imports": ["os", "sys", "very_long_module_name"],
        "comments": ["NOQA", "comment2"],
        "comment_prefix": " #",
        "line_length": 20,
    }
    result = noqa(**interface)
    assert result == "import os, sys, very_long_module_name # NOQA comment2"


def test_noqa_wrap_mode_with_comments_does_not_fit_and_no_noqa():
    interface = {
        "statement": "import ",
        "imports": ["os", "sys", "very_long_module_name"],
        "comments": ["comment1"],
        "comment_prefix": " #",
        "line_length": 20,
    }
    result = noqa(**interface)
    assert result == "import os, sys, very_long_module_name # NOQA comment1"


def test_noqa_wrap_mode_no_comments_fits_line():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 20,
    }
    result = noqa(**interface)
    assert result == "import os"


def test_noqa_wrap_mode_no_comments_exceeds_line():
    interface = {
        "statement": "import ",
        "imports": ["os", "sys", "very_long_module_name"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 10,
    }
    result = noqa(**interface)
    assert result == "import os, sys, very_long_module_name # NOQA"
