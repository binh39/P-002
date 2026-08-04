# file: src\sample_repo\isort\isort\api.py:241-305
# asked: {"lines": [241, 242, 243, 244, 245, 246, 247, 248, 249, 262, 264, 265, 267, 268, 270, 271, 272, 273, 275, 276, 278, 279, 280, 281, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 296, 298, 299, 300, 301, 302, 303, 305], "branches": [[264, 265], [264, 267], [278, 279], [278, 283], [279, 280], [279, 281], [284, 285], [284, 305]]}
# gained: {"lines": [241, 243, 244, 246, 247, 262, 264, 265, 267, 268, 270, 271, 272, 273, 275, 276, 278, 279, 280, 281, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 296, 298, 299, 300, 301, 302, 303, 305], "branches": [[264, 265], [264, 267], [278, 279], [278, 283], [279, 280], [279, 281], [284, 285], [284, 305]]}

from io import StringIO
from pathlib import Path
from isort.api import check_stream
from isort.settings import Config


def test_check_stream_sorted(tmp_path):
    # Already sorted imports, verbose=False, should return True
    d = tmp_path / "sub"
    d.mkdir()
    p = d / "test.py"
    p.write_text("import os\nimport sys\n")
    
    stream = StringIO("import os\nimport sys\n")
    assert check_stream(stream, file_path=p) is True


def test_check_stream_sorted_verbose(tmp_path):
    # Already sorted imports, verbose=True, should return True and print success message
    d = tmp_path / "sub"
    d.mkdir()
    p = d / "test.py"
    p.write_text("import os\nimport sys\n")

    stream = StringIO("import os\nimport sys\n")
    config = Config(verbose=True)
    assert check_stream(stream, config=config, file_path=p) is True


def test_check_stream_unsorted_no_diff(tmp_path):
    # Unsorted imports, show_diff=False, should return False
    d = tmp_path / "sub"
    d.mkdir()
    p = d / "test.py"
    p.write_text("import sys\nimport os\n")

    stream = StringIO("import sys\nimport os\n")
    assert check_stream(stream, show_diff=False, file_path=p) is False


def test_check_stream_unsorted_with_diff_true(tmp_path):
    # Unsorted imports, show_diff=True, should return False and print diff
    d = tmp_path / "sub"
    d.mkdir()
    p = d / "test.py"
    p.write_text("import sys\nimport os\n")

    stream = StringIO("import sys\nimport os\n")
    assert check_stream(stream, show_diff=True, file_path=p) is False


def test_check_stream_unsorted_with_diff_stream(tmp_path):
    # Unsorted imports, show_diff as a StringIO stream, should return False and write diff to stream
    d = tmp_path / "sub"
    d.mkdir()
    p = d / "test.py"
    p.write_text("import sys\nimport os\n")

    stream = StringIO("import sys\nimport os\n")
    diff_output = StringIO()
    assert check_stream(stream, show_diff=diff_output, file_path=p) is False
    diff_content = diff_output.getvalue()
    assert len(diff_content) > 0
