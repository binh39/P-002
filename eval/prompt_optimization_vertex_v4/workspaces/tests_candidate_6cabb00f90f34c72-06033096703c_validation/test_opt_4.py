# file: src\sample_repo\isort\isort\api.py:241-305
# asked: {"lines": [241, 242, 243, 244, 245, 246, 247, 248, 249, 262, 264, 265, 267, 268, 270, 271, 272, 273, 275, 276, 278, 279, 280, 281, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 296, 298, 299, 300, 301, 302, 303, 305], "branches": [[264, 265], [264, 267], [278, 279], [278, 283], [279, 280], [279, 281], [284, 285], [284, 305]]}
# gained: {"lines": [241, 243, 244, 246, 247, 262, 264, 265, 267, 268, 270, 271, 272, 273, 275, 276, 278, 279, 280, 281, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 296, 298, 299, 300, 301, 302, 303, 305], "branches": [[264, 265], [264, 267], [278, 279], [278, 283], [279, 280], [284, 285]]}

from io import StringIO
from pathlib import Path
from isort.api import check_stream
from isort.settings import Config


def test_check_stream_already_sorted_verbose(tmp_path):
    p = tmp_path / "test.py"
    p.write_text("import os\nimport sys\n")
    stream = StringIO("import os\nimport sys\n")
    config = Config(verbose=True, only_modified=False)
    result = check_stream(input_stream=stream, config=config, file_path=p)
    assert result is True


def test_check_stream_incorrectly_sorted_with_diff_true(tmp_path):
    p = tmp_path / "test.py"
    p.write_text("import sys\nimport os\n")
    stream = StringIO("import sys\nimport os\n")
    diff_output = StringIO()
    result = check_stream(
        input_stream=stream,
        show_diff=diff_output,
        file_path=p,
    )
    assert result is False
    assert diff_output.getvalue() != ""


def test_check_stream_incorrectly_sorted_with_diff_boolean(tmp_path):
    p = tmp_path / "test.py"
    p.write_text("import sys\nimport os\n")
    stream = StringIO("import sys\nimport os\n")
    result = check_stream(
        input_stream=stream,
        show_diff=True,
        file_path=p,
    )
    assert result is False
