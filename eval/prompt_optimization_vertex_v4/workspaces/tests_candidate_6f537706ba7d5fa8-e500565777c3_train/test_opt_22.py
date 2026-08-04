# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}

from isort.wrap_modes import noqa


def test_noqa_wrap_mode_with_comments_short_line():
    # Covers lines 243-253
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": ["custom"],
        "comment_prefix": "#",
        "line_length": 80,
    }
    result = noqa(**interface)
    assert result == "import os# custom"


def test_noqa_wrap_mode_with_comments_long_line_has_noqa():
    # Covers lines 243-248, 254-255
    interface = {
        "statement": "import ",
        "imports": ["very_long_module_name_that_exceeds_length"],
        "comments": ["NOQA", "extra"],
        "comment_prefix": "#",
        "line_length": 10,
    }
    result = noqa(**interface)
    assert result == "import very_long_module_name_that_exceeds_length# NOQA extra"


def test_noqa_wrap_mode_with_comments_long_line_no_noqa():
    # Covers lines 243-248, 256
    interface = {
        "statement": "import ",
        "imports": ["very_long_module_name_that_exceeds_length"],
        "comments": ["extra"],
        "comment_prefix": "#",
        "line_length": 10,
    }
    result = noqa(**interface)
    assert result == "import very_long_module_name_that_exceeds_length# NOQA extra"


def test_noqa_wrap_mode_no_comments_short_line():
    # Covers lines 243-248 (False), 258-259
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": [],
        "comment_prefix": "#",
        "line_length": 80,
    }
    result = noqa(**interface)
    assert result == "import os"


def test_noqa_wrap_mode_no_comments_long_line():
    # Covers lines 243-248 (False), 258, 260
    interface = {
        "statement": "import ",
        "imports": ["very_long_module_name_that_exceeds_length"],
        "comments": [],
        "comment_prefix": "#",
        "line_length": 10,
    }
    result = noqa(**interface)
    assert result == "import very_long_module_name_that_exceeds_length# NOQA"
