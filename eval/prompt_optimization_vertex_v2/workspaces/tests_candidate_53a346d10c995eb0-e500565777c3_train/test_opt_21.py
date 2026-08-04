# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}

import pytest
from isort.wrap_modes import noqa


def test_noqa_with_comments_short_line():
    # Covers: interface["comments"] is truthy, and length fits within line_length (line 253)
    res = noqa(
        statement="import ",
        imports=["os"],
        comments=["comment"],
        comment_prefix="#",
        line_length=50,
    )
    assert res == "import os# comment"


def test_noqa_with_comments_noqa_in_comments():
    # Covers: interface["comments"] is truthy, length exceeds line_length, but "NOQA" is in comments (line 255)
    res = noqa(
        statement="import ",
        imports=["os", "sys"],
        comments=["NOQA"],
        comment_prefix="#",
        line_length=10,
    )
    assert res == "import os, sys# NOQA"


def test_noqa_with_comments_no_noqa_in_comments():
    # Covers: interface["comments"] is truthy, length exceeds line_length, and "NOQA" not in comments (line 256)
    res = noqa(
        statement="import ",
        imports=["os", "sys"],
        comments=["comment"],
        comment_prefix="#",
        line_length=10,
    )
    assert res == "import os, sys# NOQA comment"


def test_noqa_without_comments_short_line():
    # Covers: interface["comments"] is empty/falsy, and len(retval) <= line_length (line 259)
    res = noqa(
        statement="import ",
        imports=["os"],
        comments=[],
        comment_prefix="#",
        line_length=50,
    )
    assert res == "import os"


def test_noqa_without_comments_long_line():
    # Covers: interface["comments"] is empty/falsy, and len(retval) > line_length (line 260)
    res = noqa(
        statement="import ",
        imports=["os", "sys"],
        comments=[],
        comment_prefix="#",
        line_length=5,
    )
    assert res == "import os, sys# NOQA"
