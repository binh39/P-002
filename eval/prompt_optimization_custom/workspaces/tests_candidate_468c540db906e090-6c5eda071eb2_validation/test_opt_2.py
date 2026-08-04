# file: src\sample_repo\isort\isort\api.py:241-305
# asked: {"lines": [241, 242, 243, 244, 245, 246, 247, 248, 249, 262, 264, 265, 267, 268, 270, 271, 272, 273, 275, 276, 278, 279, 280, 281, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 296, 298, 299, 300, 301, 302, 303, 305], "branches": [[264, 265], [264, 267], [278, 279], [278, 283], [279, 280], [279, 281], [284, 285], [284, 305]]}
# gained: {"lines": [241, 243, 244, 246, 247, 262, 264, 265, 267, 268, 270, 271, 272, 273, 275, 276, 278, 279, 281, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 296, 298, 299, 300, 301, 302, 303, 305], "branches": [[264, 265], [264, 267], [278, 279], [278, 283], [279, 281], [284, 285], [284, 305]]}

import pytest
from io import StringIO
from pathlib import Path
from isort.api import check_stream
from isort.settings import Config

@pytest.fixture
def input_stream():
    return StringIO("import os\nimport sys\n")

@pytest.fixture
def unsorted_input_stream():
    return StringIO("import sys\nimport os\n")

@pytest.fixture
def config():
    return Config()

def test_check_stream_no_changes(input_stream, config):
    result = check_stream(input_stream=input_stream, config=config)
    assert result is True

def test_check_stream_with_changes(unsorted_input_stream, config):
    result = check_stream(unsorted_input_stream, show_diff=True, config=config)
    assert result is False


def test_check_stream_with_file_path(unsorted_input_stream, config):
    # Create a temporary file to avoid skipping due to config settings
    file_path = Path("test_file.py")
    with open(file_path, 'w') as f:
        f.write(unsorted_input_stream.getvalue())
    result = check_stream(StringIO(unsorted_input_stream.getvalue()), file_path=file_path, config=config)
    assert result is False

def test_check_stream_disregard_skip(unsorted_input_stream, config):
    # Create a new config instance to avoid FrozenInstanceError
    config = Config(skip=frozenset())  # Ensure no files are skipped
    result = check_stream(unsorted_input_stream, disregard_skip=True, config=config)
    assert result is False

def test_check_stream_with_color_output(unsorted_input_stream, config):
    # Create a new config instance to avoid FrozenInstanceError
    config = Config(color_output=True)
    result = check_stream(unsorted_input_stream, config=config)
    assert result is False
