# file: src\sample_repo\isort\isort\api.py:537-576
# asked: {"lines": [537, 538, 539, 540, 541, 542, 543, 544, 545, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [571, 574], [574, 564], [574, 575]]}
# gained: {"lines": [537, 540, 541, 542, 543, 556, 557, 558, 560, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [574, 564], [574, 575]]}

import io
from isort.api import find_imports_in_stream, ImportKey

def test_find_imports_in_stream_unique_variations():
    code = (
        "import os\n"
        "import os\n"
        "from os import path\n"
        "from os import path as p\n"
        "import sys\n"
        "import sys\n"
    )

    # Test unique=True / ImportKey.ALIAS
    stream1 = io.StringIO(code)
    results_alias = list(find_imports_in_stream(stream1, unique=ImportKey.ALIAS))
    assert len(results_alias) > 0

    stream1_true = io.StringIO(code)
    results_true = list(find_imports_in_stream(stream1_true, unique=True))
    assert len(results_true) > 0

    # Test unique=ImportKey.ATTRIBUTE
    stream2 = io.StringIO("from os import path\nfrom os import path\n")
    results_attr = list(find_imports_in_stream(stream2, unique=ImportKey.ATTRIBUTE))
    assert len(results_attr) == 1

    # Test unique=ImportKey.MODULE
    stream3 = io.StringIO("import os.path\nimport os.path\nimport os.environ\n")
    results_mod = list(find_imports_in_stream(stream3, unique=ImportKey.MODULE))
    assert len(results_mod) == 2

    # Test unique=ImportKey.PACKAGE
    stream4 = io.StringIO("import os.path\nimport os.environ\nimport sys.path\n")
    results_pkg = list(find_imports_in_stream(stream4, unique=ImportKey.PACKAGE))
    assert len(results_pkg) == 2

    # Test with existing _seen set
    stream5 = io.StringIO("import os\nimport sys\n")
    seen_set = {"os"}
    results_seen = list(find_imports_in_stream(stream5, unique=ImportKey.MODULE, _seen=seen_set))
    modules = [imp.module for imp in results_seen]
    assert "os" not in modules
    assert "sys" in modules
