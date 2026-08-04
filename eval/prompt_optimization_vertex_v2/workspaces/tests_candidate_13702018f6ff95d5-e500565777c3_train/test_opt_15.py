# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}

import pytest
from isort.wrap_modes import noqa

def test_noqa_with_comments_fits_line():
    # Covers:
    # - interface["comments"] is truthy
    # - length of retval + comment_prefix + 1 + comment_str <= line_length
    result = noqa(
        statement="from foo import ",
        imports=["bar"],
        comments=["# comment"],
        comment_prefix="  #",
        line_length=40,
    )
    assert result == "from foo import bar  # # comment"


def test_noqa_with_comments_has_noqa_in_comments():
    # Covers:
    # - interface["comments"] is truthy
    # - length exceeds line_length
    # - "NOQA" in interface["comments"]
    result = noqa(
        statement="from foo import ",
        imports=["bar_very_long_import_name"],
        comments=["NOQA"],
        comment_prefix="  #",
        line_length=20,
    )
    assert result == "from foo import bar_very_long_import_name  # NOQA"


def test_noqa_with_comments_no_noqa_in_comments():
    # Covers:
    # - interface["comments"] is truthy
    # - length exceeds line_length
    # - "NOQA" not in interface["comments"] (inserts "NOQA")
    result = noqa(
        statement="from foo import ",
        imports=["bar_very_long_import_name"],
        comments=["# custom"],
        comment_prefix="  #",
        line_length=20,
    )
    assert result == "from foo import bar_very_long_import_name  # NOQA # custom"


def test_noqa_without_comments_fits_line():
    # Covers:
    # - interface["comments"] is falsy (empty)
    # - len(retval) <= interface["line_length"] (lines 258-259)
    result = noqa(
        statement="import ",
        imports=["foo"],
        comments=[],
        comment_prefix="  #",
        line_length=20,
    )
    assert result == "import foo"


def test_noqa_without_comments_exceeds_line():
    # Covers:
    # - interface["comments"] is falsy (empty)
    # - len(retval) > interface["line_length"] (line 260)
    result = noqa(
        statement="import ",
        imports=["foo_very_long_import_name"],
        comments=[],
        comment_prefix="  #",
        line_length=15,
    )
    assert result == "import foo_very_long_import_name  # NOQA"
