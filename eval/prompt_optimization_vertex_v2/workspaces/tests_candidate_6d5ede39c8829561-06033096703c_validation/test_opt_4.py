# file: src\sample_repo\isort\isort\api.py:241-305
# asked: {"lines": [241, 242, 243, 244, 245, 246, 247, 248, 249, 262, 264, 265, 267, 268, 270, 271, 272, 273, 275, 276, 278, 279, 280, 281, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 296, 298, 299, 300, 301, 302, 303, 305], "branches": [[264, 265], [264, 267], [278, 279], [278, 283], [279, 280], [279, 281], [284, 285], [284, 305]]}
# gained: {"lines": [241, 243, 244, 246, 247, 262, 264, 265, 267, 268, 270, 271, 272, 273, 275, 276, 278, 279, 280, 281, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 296, 298, 299, 300, 301, 302, 303, 305], "branches": [[264, 265], [264, 267], [278, 279], [278, 283], [279, 280], [279, 281], [284, 285], [284, 305]]}

from io import StringIO
from pathlib import Path
from isort.api import check_stream
from isort.settings import Config


def test_check_stream_already_sorted_verbose():
    # Covers:
    # - not changed (returns True)
    # - config.verbose and not config.only_modified (printer.success branch)
    stream = StringIO("import os\nimport sys\n")
    config = Config(verbose=True, only_modified=False)
    result = check_stream(input_stream=stream, config=config, file_path=Path("test_file.py"), disregard_skip=True)
    assert result is True


def test_check_stream_already_sorted_not_verbose():
    # Covers:
    # - not changed (returns True)
    # - not config.verbose
    stream = StringIO("import os\nimport sys\n")
    config = Config(verbose=False)
    result = check_stream(input_stream=stream, config=config, file_path=Path("test_file.py"), disregard_skip=True)
    assert result is True


def test_check_stream_unsorted_no_show_diff():
    # Covers:
    # - changed (returns False)
    # - show_diff = False
    stream = StringIO("import sys\nimport os\n")
    result = check_stream(input_stream=stream, file_path=Path("test_file.py"), disregard_skip=True)
    assert result is False


def test_check_stream_unsorted_with_show_diff_bool():
    # Covers:
    # - changed (returns False)
    # - show_diff = True (diff output printed to stdout / handled internally)
    stream = StringIO("import sys\nimport os\n")
    result = check_stream(input_stream=stream, show_diff=True, file_path=Path("test_file.py"), disregard_skip=True)
    assert result is False


def test_check_stream_unsorted_with_show_diff_stream():
    # Covers:
    # - changed (returns False)
    # - show_diff as a TextIO stream
    stream = StringIO("import sys\nimport os\n")
    diff_output = StringIO()
    result = check_stream(input_stream=stream, show_diff=diff_output, file_path=Path("test_file.py"), disregard_skip=True)
    assert result is False
    diff_output.seek(0)
    assert len(diff_output.read()) > 0
