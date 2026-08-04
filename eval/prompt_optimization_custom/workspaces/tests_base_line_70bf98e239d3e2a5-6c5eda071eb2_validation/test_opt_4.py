# file: src\sample_repo\isort\isort\api.py:138-238
# asked: {"lines": [138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 176, 177, 178, 179, 180, 181, 182, 183, 185, 187, 188, 189, 190, 192, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 206, 208, 209, 211, 212, 213, 214, 215, 216, 217, 219, 220, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 235, 236, 238], "branches": [[163, 164], [163, 187], [189, 190], [189, 192], [194, 195], [194, 211], [199, 200], [199, 201], [201, 202], [201, 206], [208, 209], [208, 211], [222, 223], [222, 238], [228, 229], [228, 230], [230, 231], [230, 235], [235, 236], [235, 238]]}
# gained: {"lines": [138, 141, 143, 144, 145, 146, 162, 163, 187, 188, 189, 190, 192, 194, 211, 212, 213, 214, 215, 216, 217, 222, 238], "branches": [[163, 187], [189, 190], [189, 192], [194, 211], [222, 238]]}

import pytest
from io import StringIO
from pathlib import Path
from isort.api import sort_stream
from isort.exceptions import ExistingSyntaxErrors, FileSkipSetting, IntroducedSyntaxErrors
from isort.settings import Config

@pytest.fixture
def mock_config():
    """Fixture to create a mock config for testing."""
    config = Config()
    # Use frozenset to set skips and skip_globs as they are properties
    config._skips = frozenset()
    config._skip_globs = frozenset()
    return config


def test_sort_stream_with_file_skip_setting(mock_config):
    """Test sort_stream raises FileSkipSetting when file is skipped."""
    mock_config._skips = frozenset(['test_file.py'])
    file_path = Path('test_file.py')
    input_code = "import os\nimport sys\n"
    input_stream = StringIO(input_code)
    output_stream = StringIO()

    with pytest.raises(FileSkipSetting):
        sort_stream(input_stream, output_stream, file_path=file_path, config=mock_config)

def test_sort_stream_with_valid_code(mock_config):
    """Test sort_stream processes valid code correctly."""
    input_code = "import os\nimport sys\n"
    expected_output = "import os\nimport sys\n"  # No change expected
    input_stream = StringIO(input_code)
    output_stream = StringIO()

    changed = sort_stream(input_stream, output_stream, config=mock_config)

    assert not changed  # No changes should be made
    assert output_stream.getvalue() == expected_output

def test_sort_stream_with_changes(mock_config):
    """Test sort_stream processes code and makes changes."""
    input_code = "import sys\nimport os\n"
    expected_output = "import os\nimport sys\n"  # Expected sorted output
    input_stream = StringIO(input_code)
    output_stream = StringIO()

    changed = sort_stream(input_stream, output_stream, config=mock_config)

    assert changed  # Changes should be made
    assert output_stream.getvalue() == expected_output

def test_sort_stream_with_cython_extension(mock_config):
    """Test sort_stream with a Cython extension that raises no errors."""
    input_code = "import numpy as np\n"
    expected_output = "import numpy as np\n"  # No change expected
    input_stream = StringIO(input_code)
    output_stream = StringIO()

    # Simulate a Cython extension
    changed = sort_stream(input_stream, output_stream, extension='pyx', config=mock_config)

    assert not changed  # No changes should be made
    assert output_stream.getvalue() == expected_output
