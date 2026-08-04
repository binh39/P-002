# file: src\sample_repo\isort\isort\api.py:537-576
# asked: {"lines": [537, 538, 539, 540, 541, 542, 543, 544, 545, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [571, 574], [574, 564], [574, 575]]}
# gained: {"lines": [537, 540, 541, 542, 543, 556, 557, 558, 560, 561, 563, 564], "branches": [[560, 561], [564, 0]]}

import pytest
from io import StringIO
from pathlib import Path
from isort import identify
from isort.settings import Config
from isort.api import find_imports_in_stream
from enum import Enum

class ImportKey(Enum):
    """Defines how to key an individual import, generally for deduping."""
    PACKAGE = 1
    MODULE = 2
    ATTRIBUTE = 3
    ALIAS = 4

@pytest.fixture
def sample_code():
    return StringIO(
        "import os\n"
        "import sys\n"
        "from collections import defaultdict\n"
        "from collections import Counter as C\n"
        "\n"
        "def example_function():\n"
        "    pass\n"
    )

def test_find_imports_in_stream_no_unique(sample_code):
    """Test without unique flag to yield all imports."""
    result = list(find_imports_in_stream(sample_code, unique=False))
    assert len(result) == 4
    assert result[0].statement() == "import os"
    assert result[1].statement() == "import sys"
    assert result[2].statement() == "from collections import defaultdict"
    assert result[3].statement() == "from collections import Counter as C"




