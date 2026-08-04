# file: src\sample_repo\isort\isort\api.py:241-305
# asked: {"lines": [241, 242, 243, 244, 245, 246, 247, 248, 249, 262, 264, 265, 267, 268, 270, 271, 272, 273, 275, 276, 278, 279, 280, 281, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 296, 298, 299, 300, 301, 302, 303, 305], "branches": [[264, 265], [264, 267], [278, 279], [278, 283], [279, 280], [279, 281], [284, 285], [284, 305]]}
# gained: {"lines": [241, 243, 244, 246, 247, 262, 264, 265, 267, 268, 270, 271, 272, 273, 275, 276, 278, 279, 280, 281, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 296, 298, 299, 300, 301, 302, 303, 305], "branches": [[264, 265], [264, 267], [278, 279], [278, 283], [279, 280], [279, 281], [284, 285], [284, 305]]}

from io import StringIO
from pathlib import Path
from isort.api import check_stream
from isort.settings import Config


def test_check_stream_sorted():
    # Already sorted imports, verbose=False -> returns True, no verbose success message
    stream = StringIO("import os\nimport sys\n")
    assert check_stream(stream) is True


def test_check_stream_sorted_verbose():
    # Already sorted imports with verbose=True and only_modified=False -> exercises printer.success
    stream = StringIO("import os\nimport sys\n")
    # Using an explicit non-skipped filename like "test_file.py" or just no file_path or disregard_skip=True
    config = Config(verbose=True, only_modified=False)
    assert check_stream(stream, config=config, file_path=Path("test_file.py"), disregard_skip=True) is True


def test_check_stream_unsorted_no_diff():
    # Unsorted imports, show_diff=False -> returns False, prints error, no diff branch
    stream = StringIO("import sys\nimport os\n")
    assert check_stream(stream, show_diff=False) is False


def test_check_stream_unsorted_with_diff_bool():
    # Unsorted imports, show_diff=True (bool) -> exercises show_diff code block with output=None
    stream = StringIO("import sys\nimport os\n")
    assert check_stream(stream, show_diff=True) is False


def test_check_stream_unsorted_with_diff_stream():
    # Unsorted imports, show_diff as TextIO stream -> exercises show_unified_diff with custom output stream
    stream = StringIO("import sys\nimport os\n")
    diff_output = StringIO()
    assert check_stream(stream, show_diff=diff_output) is False
    diff_output.seek(0)
    assert len(diff_output.read()) > 0
