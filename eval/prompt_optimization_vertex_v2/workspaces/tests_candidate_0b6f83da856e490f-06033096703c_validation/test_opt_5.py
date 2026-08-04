# file: src\sample_repo\isort\isort\api.py:241-305
# asked: {"lines": [241, 242, 243, 244, 245, 246, 247, 248, 249, 262, 264, 265, 267, 268, 270, 271, 272, 273, 275, 276, 278, 279, 280, 281, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 296, 298, 299, 300, 301, 302, 303, 305], "branches": [[264, 265], [264, 267], [278, 279], [278, 283], [279, 280], [279, 281], [284, 285], [284, 305]]}
# gained: {"lines": [241, 243, 244, 246, 247, 262, 264, 267, 268, 270, 271, 272, 273, 275, 276, 278, 279, 280, 281, 283, 284, 305], "branches": [[264, 267], [278, 279], [278, 283], [279, 280], [279, 281], [284, 305]]}

from io import StringIO
from pathlib import Path
from isort.api import check_stream
from isort.settings import Config


def test_check_stream_sorted_no_verbose():
    stream = StringIO("import a\nimport b\n")
    result = check_stream(input_stream=stream)
    assert result is True


def test_check_stream_sorted_verbose():
    stream = StringIO("import a\nimport b\n")
    config = Config(verbose=True, only_modified=False)
    # Avoid file_path existing check or file-based skip check if no file path is needed,
    # or pass a dummy file path without relying on tmp_path if tmp_path has permission issues on Windows.
    result = check_stream(input_stream=stream, config=config, file_path=Path("nonexistent.py"), disregard_skip=True)
    assert result is True


def test_check_stream_unsorted_no_diff():
    stream = StringIO("import b\nimport a\n")
    result = check_stream(input_stream=stream, show_diff=False)
    assert result is False




