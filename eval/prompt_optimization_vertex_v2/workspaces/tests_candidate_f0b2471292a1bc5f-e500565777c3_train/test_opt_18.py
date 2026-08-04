# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}

import pytest
from isort.wrap_modes import noqa

def test_noqa_wrap_mode_with_comments_fits_line_length():
    # Covers: interface["comments"] is True, and length <= line_length (line 253)
    result = noqa(
        statement="import ",
        imports=["os"],
        comments=["comment"],
        comment_prefix="  #",
        line_length=30,
    )
    assert result == "import os  # comment"

def test_noqa_wrap_mode_with_comments_exceeds_line_length_has_noqa():
    # Covers: interface["comments"] is True, length > line_length, but "NOQA" in interface["comments"] (line 255)
    result = noqa(
        statement="import ",
        imports=["os", "sys", "math"],
        comments=["NOQA"],
        comment_prefix="  #",
        line_length=15,
    )
    assert result == "import os, sys, math  # NOQA"

def test_noqa_wrap_mode_with_comments_exceeds_line_length_no_noqa():
    # Covers: interface["comments"] is True, length > line_length, and "NOQA" not in interface["comments"] (line 256)
    result = noqa(
        statement="import ",
        imports=["os", "sys", "math"],
        comments=["comment"],
        comment_prefix="  #",
        line_length=15,
    )
    assert result == "import os, sys, math  # NOQA comment"

def test_noqa_wrap_mode_no_comments_fits_line_length():
    # Covers: interface["comments"] is False, and len(retval) <= line_length (line 259)
    result = noqa(
        statement="import ",
        imports=["os"],
        comments=[],
        comment_prefix="  #",
        line_length=20,
    )
    assert result == "import os"

def test_noqa_wrap_mode_no_comments_exceeds_line_length():
    # Covers: interface["comments"] is False, and len(retval) > line_length (line 260)
    result = noqa(
        statement="import ",
        imports=["os", "sys", "math"],
        comments=[],
        comment_prefix="  #",
        line_length=10,
    )
    assert result == "import os, sys, math  # NOQA"
