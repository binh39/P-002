# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}

import pytest
from isort.wrap_modes import noqa

def test_noqa_mode_with_comments_within_line_length():
    # Covers: interface["comments"] is truthy, and length <= line_length (line 253)
    result = noqa(
        statement="import ",
        imports=["os", "sys"],
        comments=["# comment"],
        comment_prefix="  #",
        line_length=40,
    )
    # retval = "import os, sys" (len 14)
    # comment_prefix = "  #" (len 3)
    # comment_str = "# comment" (len 9)
    # total len = 14 + 3 + 1 + 9 = 27 <= 40
    assert result == "import os, sys  # # comment"

def test_noqa_mode_with_comments_exceeding_line_length_but_has_noqa():
    # Covers: interface["comments"] is truthy, length > line_length, but "NOQA" in interface["comments"] (line 255)
    result = noqa(
        statement="import ",
        imports=["os", "sys", "math", "re"],
        comments=["NOQA"],
        comment_prefix="  #",
        line_length=20,
    )
    # retval = "import os, sys, math, re" (len 26) > line_length (20)
    # "NOQA" is in interface["comments"]
    assert result == "import os, sys, math, re  # NOQA"

def test_noqa_mode_with_comments_exceeding_line_length_without_noqa():
    # Covers: interface["comments"] is truthy, length > line_length, "NOQA" not in interface["comments"] (line 256)
    result = noqa(
        statement="import ",
        imports=["os", "sys", "math", "re"],
        comments=["custom_comment"],
        comment_prefix="  #",
        line_length=20,
    )
    # retval = "import os, sys, math, re" (len 26) > line_length (20)
    # "NOQA" is NOT in interface["comments"]
    assert result == "import os, sys, math, re  # NOQA custom_comment"

def test_noqa_mode_without_comments_within_line_length():
    # Covers: interface["comments"] is empty/falsy, len(retval) <= line_length (line 259)
    result = noqa(
        statement="import ",
        imports=["os"],
        comments=[],
        comment_prefix="  #",
        line_length=20,
    )
    # retval = "import os" (len 9) <= 20
    assert result == "import os"

def test_noqa_mode_without_comments_exceeding_line_length():
    # Covers: interface["comments"] is empty/falsy, len(retval) > line_length (line 260)
    result = noqa(
        statement="import ",
        imports=["os", "sys", "math", "re"],
        comments=[],
        comment_prefix="  #",
        line_length=15,
    )
    # retval = "import os, sys, math, re" (len 26) > 15
    assert result == "import os, sys, math, re  # NOQA"
