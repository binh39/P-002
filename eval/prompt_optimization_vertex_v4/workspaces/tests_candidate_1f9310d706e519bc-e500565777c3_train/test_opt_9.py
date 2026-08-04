# file: src\sample_repo\isort\isort\api.py:537-576
# asked: {"lines": [537, 538, 539, 540, 541, 542, 543, 544, 545, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [571, 574], [574, 564], [574, 575]]}
# gained: {"lines": [537, 540, 541, 542, 543, 556, 557, 558, 560, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [574, 564], [574, 575]]}

import io
from isort.api import find_imports_in_stream, ImportKey
from isort.settings import DEFAULT_CONFIG


def test_find_imports_in_stream_unique_variations():
    code = (
        "import os\n"
        "import os\n"
        "from os import path\n"
        "from os import path as p\n"
        "import sys.path\n"
        "import sys.version\n"
        "from collections import OrderedDict\n"
    )

    # Test unique=True (or ImportKey.ALIAS)
    stream = io.StringIO(code)
    results_true = list(find_imports_in_stream(stream, unique=True))
    assert len(results_true) > 0

    # Test unique=ImportKey.ATTRIBUTE
    stream = io.StringIO(code)
    results_attr = list(find_imports_in_stream(stream, unique=ImportKey.ATTRIBUTE))
    assert len(results_attr) > 0

    # Test unique=ImportKey.MODULE
    stream = io.StringIO(code)
    results_mod = list(find_imports_in_stream(stream, unique=ImportKey.MODULE))
    assert len(results_mod) > 0

    # Test unique=ImportKey.PACKAGE
    stream = io.StringIO(code)
    results_pkg = list(find_imports_in_stream(stream, unique=ImportKey.PACKAGE))
    assert len(results_pkg) > 0

    # Test with _seen passed in and duplicate key filtering
    stream = io.StringIO("import os\nimport os\n")
    seen = set()
    results_seen = list(find_imports_in_stream(stream, unique=ImportKey.MODULE, _seen=seen))
    assert len(results_seen) == 1
    assert "os" in seen
