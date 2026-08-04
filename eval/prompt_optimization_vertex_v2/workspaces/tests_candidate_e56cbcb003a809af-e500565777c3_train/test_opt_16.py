# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 254, 255, 258, 260], "branches": [[248, 249], [248, 258], [249, 254], [254, 255], [258, 260]]}

import pytest
from isort.wrap_modes import noqa

def test_noqa_wrap_mode_lines_243_260():
    # Test case 1: interface["comments"] is present, length exceeds line_length, but "NOQA" is in comments (line 254-255)
    interface_with_noqa_comment = {
        "statement": "from module import ",
        "imports": ["a", "b", "c", "d"],
        "comments": ["NOQA", "custom"],
        "comment_prefix": "  #",
        "line_length": 10,
    }
    res1 = noqa(**interface_with_noqa_comment)
    assert "NOQA" in res1

    # Test case 2: interface["comments"] is empty, length exceeds line_length (line 260)
    interface_no_comments_too_long = {
        "statement": "from very_long_module_name import ",
        "imports": ["very_long_import_name"],
        "comments": [],
        "comment_prefix": "  #",
        "line_length": 10,
    }
    res2 = noqa(**interface_no_comments_too_long)
    assert res2.endswith("NOQA")
