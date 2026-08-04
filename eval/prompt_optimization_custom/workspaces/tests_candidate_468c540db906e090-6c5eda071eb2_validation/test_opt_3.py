# file: src\sample_repo\isort\isort\api.py:138-238
# asked: {"lines": [138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 176, 177, 178, 179, 180, 181, 182, 183, 185, 187, 188, 189, 190, 192, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 206, 208, 209, 211, 212, 213, 214, 215, 216, 217, 219, 220, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 235, 236, 238], "branches": [[163, 164], [163, 187], [189, 190], [189, 192], [194, 195], [194, 211], [199, 200], [199, 201], [201, 202], [201, 206], [208, 209], [208, 211], [222, 223], [222, 238], [228, 229], [228, 230], [230, 231], [230, 235], [235, 236], [235, 238]]}
# gained: {"lines": [138, 141, 143, 144, 145, 146, 162, 163, 187, 188, 189, 190], "branches": [[163, 187], [189, 190]]}

import pytest
from io import StringIO
from pathlib import Path
from isort.api import sort_stream
from isort.exceptions import ExistingSyntaxErrors, FileSkipSetting, IntroducedSyntaxErrors
from isort.settings import Config

@pytest.fixture
def input_stream():
    return StringIO("import os\nimport sys\n")

@pytest.fixture
def output_stream():
    return StringIO()

@pytest.fixture
def config():
    return Config()



def test_sort_stream_with_file_skip_setting(input_stream, output_stream, config):
    # Create a new config instance to avoid FrozenInstanceError
    new_config = Config(skip={"test.py"})  # Simulate a file skip
    input_stream = StringIO("import os\n")
    with pytest.raises(FileSkipSetting):
        sort_stream(
            input_stream=input_stream,
            output_stream=output_stream,
            config=new_config,
            file_path=Path("test.py")
        )


