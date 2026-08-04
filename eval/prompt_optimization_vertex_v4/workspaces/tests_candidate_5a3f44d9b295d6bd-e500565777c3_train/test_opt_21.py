# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}

import pytest
from isort.wrap_modes import noqa

def test_noqa_wrap_mode_lines_243_260():
    # Test case 1: comments present, length <= line_length (line 253)
    interface_case1 = {
        "statement": "from module import ",
        "imports": ["a"],
        "comments": ["comment1"],
        "comment_prefix": " #",
        "line_length": 50,
    }
    res1 = noqa(**interface_case1)
    assert res1 == "from module import a # comment1"

    # Test case 2: comments present, length > line_length, but "NOQA" is in comments (line 255)
    interface_case2 = {
        "statement": "from very_long_module_name_that_exceeds_length import ",
        "imports": ["a"],
        "comments": ["NOQA"],
        "comment_prefix": " #",
        "line_length": 20,
    }
    res2 = noqa(**interface_case2)
    assert res2 == "from very_long_module_name_that_exceeds_length import a # NOQA"

    # Test case 3: comments present, length > line_length, "NOQA" NOT in comments (line 256)
    interface_case3 = {
        "statement": "from very_long_module_name_that_exceeds_length import ",
        "imports": ["a"],
        "comments": ["comment1"],
        "comment_prefix": " #",
        "line_length": 20,
    }
    res3 = noqa(**interface_case3)
    assert res3 == "from very_long_module_name_that_exceeds_length import a # NOQA comment1"

    # Test case 4: no comments, length <= line_length (line 259)
    interface_case4 = {
        "statement": "from module import ",
        "imports": ["a"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 50,
    }
    res4 = noqa(**interface_case4)
    assert res4 == "from module import a"

    # Test case 5: no comments, length > line_length (line 260)
    interface_case5 = {
        "statement": "from very_long_module_name_that_exceeds_length import ",
        "imports": ["a"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 20,
    }
    res5 = noqa(**interface_case5)
    assert res5 == "from very_long_module_name_that_exceeds_length import a # NOQA"
