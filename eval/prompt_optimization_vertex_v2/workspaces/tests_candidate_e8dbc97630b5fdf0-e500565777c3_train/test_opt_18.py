# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}

from isort.wrap_modes import noqa


def test_noqa_wrap_mode_with_comments_within_line_length():
    # Covers line 248 (if interface["comments"]: True)
    # and line 253 (len <= line_length)
    result = noqa(
        statement="from module import ",
        imports=["a", "b"],
        comments=["# type: ignore"],
        comment_prefix="  #",
        line_length=50,
    )
    assert result == "from module import a, b  # # type: ignore"


def test_noqa_wrap_mode_with_comments_exceeding_line_length_with_noqa():
    # Covers line 254 ("NOQA" in interface["comments"])
    result = noqa(
        statement="from module import ",
        imports=["a", "b", "c", "d"],
        comments=["NOQA"],
        comment_prefix="  #",
        line_length=20,
    )
    assert result == "from module import a, b, c, d  # NOQA"


def test_noqa_wrap_mode_with_comments_exceeding_line_length_without_noqa():
    # Covers line 256 (returns with inserted NOQA)
    result = noqa(
        statement="from module import ",
        imports=["a", "b", "c", "d"],
        comments=["# custom comment"],
        comment_prefix="  #",
        line_length=20,
    )
    assert result == "from module import a, b, c, d  # NOQA # custom comment"


def test_noqa_wrap_mode_without_comments_within_line_length():
    # Covers line 248 (if interface["comments"]: False)
    # and line 258 (len(retval) <= line_length)
    result = noqa(
        statement="from module import ",
        imports=["a"],
        comments=[],
        comment_prefix="  #",
        line_length=30,
    )
    assert result == "from module import a"


def test_noqa_wrap_mode_without_comments_exceeding_line_length():
    # Covers line 248 (if interface["comments"]: False)
    # and line 260 (returns retval + comment_prefix + " NOQA")
    result = noqa(
        statement="from module import ",
        imports=["a", "b", "c", "d"],
        comments=[],
        comment_prefix="  #",
        line_length=20,
    )
    assert result == "from module import a, b, c, d  # NOQA"
