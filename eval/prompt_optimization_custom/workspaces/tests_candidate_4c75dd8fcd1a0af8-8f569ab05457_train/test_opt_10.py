# file: src\sample_repo\isort\isort\api.py:537-576
# asked: {"lines": [537, 538, 539, 540, 541, 542, 543, 544, 545, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [571, 574], [574, 564], [574, 575]]}
# gained: {"lines": [537, 540, 541, 542, 543, 556, 557, 558, 560, 561, 563, 564], "branches": [[560, 561], [564, 0]]}

import pytest
from io import StringIO
from pathlib import Path
from isort import identify
from isort.settings import Config
from isort.api import find_imports_in_stream

# Mocking the ImportKey Enum for testing purposes
class ImportKey:
    ALIAS = 'alias'
    ATTRIBUTE = 'attribute'
    MODULE = 'module'
    PACKAGE = 'package'

def test_find_imports_in_stream_no_unique():
    input_code = "import os\nimport sys\n"
    input_stream = StringIO(input_code)
    config = Config()
    
    result = list(find_imports_in_stream(input_stream, config=config, unique=False))
    
    assert len(result) == 2
    assert result[0].statement() == "import os"
    assert result[1].statement() == "import sys"





def test_find_imports_in_stream_top_only():
    input_code = "def my_function():\n    import os\n    import sys\n"
    input_stream = StringIO(input_code)
    config = Config()
    
    result = list(find_imports_in_stream(input_stream, config=config, top_only=True))
    
    assert len(result) == 0  # No imports should be found before the first function


