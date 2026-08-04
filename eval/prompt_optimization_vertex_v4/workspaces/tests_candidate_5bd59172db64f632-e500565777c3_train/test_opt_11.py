# file: src\sample_repo\isort\isort\api.py:537-576
# asked: {"lines": [537, 538, 539, 540, 541, 542, 543, 544, 545, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [571, 574], [574, 564], [574, 575]]}
# gained: {"lines": [537, 540, 541, 542, 543, 556, 557, 558, 560, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [574, 564], [574, 575]]}

from io import StringIO
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

    # Test unique=True / ImportKey.ALIAS / ImportKey.TRUE (True maps to statement)
    stream = StringIO(code)
    results_true = list(find_imports_in_stream(stream, unique=True))
    assert len(results_true) > 0

    stream = StringIO(code)
    results_alias = list(find_imports_in_stream(stream, unique=ImportKey.ALIAS))
    assert len(results_alias) > 0

    # Test unique=ImportKey.ATTRIBUTE
    code_attr = (
        "from os import path\n"
        "from os import path\n"
        "from os import getcwd\n"
    )
    stream = StringIO(code_attr)
    results_attr = list(find_imports_in_stream(stream, unique=ImportKey.ATTRIBUTE))
    assert len(results_attr) == 2

    # Test unique=ImportKey.MODULE
    code_mod = (
        "from os.path import join\n"
        "from os.path import dirname\n"
        "import os\n"
    )
    stream = StringIO(code_mod)
    results_mod = list(find_imports_in_stream(stream, unique=ImportKey.MODULE))
    # os.path appears twice as module, second should be skipped
    assert len(results_mod) == 2

    # Test unique=ImportKey.PACKAGE
    code_pkg = (
        "import os.path\n"
        "import os.environ\n"
        "import sys\n"
    )
    stream = StringIO(code_pkg)
    results_pkg = list(find_imports_in_stream(stream, unique=ImportKey.PACKAGE))
    # os.path and os.environ share the 'os' package, so only the first 'os' import is yielded.
    assert len(results_pkg) == 2

    # Test with pre-existing _seen set
    stream = StringIO("import os\nimport sys\n")
    seen_set = {"os"}
    results_seen = list(find_imports_in_stream(stream, unique=ImportKey.MODULE, _seen=seen_set))
    # 'os' is already in seen_set, so only 'sys' should be yielded.
    modules = [imp.module for imp in results_seen]
    assert "os" not in modules
    assert "sys" in modules
