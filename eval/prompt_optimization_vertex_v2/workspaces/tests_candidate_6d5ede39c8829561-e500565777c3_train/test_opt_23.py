# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 258, 259], "branches": [[248, 258], [258, 259]]}

import pytest
from isort.wrap_modes import noqa




def test_noqa_no_comments_short_line():
    # Covers lines 248 -> 258 -> 259 (no comments, retval <= line_length)
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": [],
        "comment_prefix": "  ",
        "line_length": 80,
    }
    result = noqa(**interface)
    assert result == "import os"

