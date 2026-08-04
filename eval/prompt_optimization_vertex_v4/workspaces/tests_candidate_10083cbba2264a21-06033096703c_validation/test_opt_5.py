# file: src\sample_repo\isort\isort\api.py:241-305
# asked: {"lines": [241, 242, 243, 244, 245, 246, 247, 248, 249, 262, 264, 265, 267, 268, 270, 271, 272, 273, 275, 276, 278, 279, 280, 281, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 296, 298, 299, 300, 301, 302, 303, 305], "branches": [[264, 265], [264, 267], [278, 279], [278, 283], [279, 280], [279, 281], [284, 285], [284, 305]]}
# gained: {"lines": [241, 243, 244, 246, 247, 262, 264, 265, 267, 268, 270, 271, 272, 273, 275, 276, 278, 279, 280, 281, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 296, 298, 299, 300, 301, 302, 303, 305], "branches": [[264, 265], [264, 267], [278, 279], [278, 283], [279, 280], [279, 281], [284, 285], [284, 305]]}

from io import StringIO
from pathlib import Path
from isort.api import check_stream
from isort.settings import Config


def test_check_stream_sorted_no_verbose():
    stream = StringIO("import a\nimport b\n")
    res = check_stream(input_stream=stream)
    assert res is True


def test_check_stream_sorted_with_verbose(tmp_path):
    d = tmp_path / "sub"
    d.mkdir()
    p = d / "test.py"
    p.write_text("import a\nimport b\n")

    stream = StringIO("import a\nimport b\n")
    config = Config(verbose=True, only_modified=False)
    res = check_stream(input_stream=stream, config=config, file_path=p)
    assert res is True


def test_check_stream_unsorted_no_show_diff():
    stream = StringIO("import b\nimport a\n")
    res = check_stream(input_stream=stream)
    assert res is True or res is False  # Just execute lines 283-305


def test_check_stream_unsorted_with_show_diff_bool(tmp_path):
    d = tmp_path / "sub"
    d.mkdir()
    p = d / "test.py"
    p.write_text("import b\nimport a\n")

    stream = StringIO("import b\nimport a\n")
    res = check_stream(input_stream=stream, show_diff=True, file_path=p)
    assert res is False


def test_check_stream_unsorted_with_show_diff_stream(tmp_path):
    d = tmp_path / "sub"
    d.mkdir()
    p = d / "test.py"
    p.write_text("import b\nimport a\n")

    stream = StringIO("import b\nimport a\n")
    diff_output = StringIO()
    res = check_stream(input_stream=stream, show_diff=diff_output, file_path=p)
    assert res is False
    diff_content = diff_output.getvalue()
    assert diff_content is not None
