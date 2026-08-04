# file: src\sample_repo\isort\isort\api.py:537-576
# asked: {"lines": [537, 538, 539, 540, 541, 542, 543, 544, 545, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [571, 574], [574, 564], [574, 575]]}
# gained: {"lines": [537, 540, 541, 542, 543, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [574, 564], [574, 575]]}

import io
from isort.api import find_imports_in_stream, ImportKey
from isort.settings import Config


def test_find_imports_in_stream_unique_variations():
    code = (
        "import os\n"
        "import os\n"
        "from os import path\n"
        "from os import path as p\n"
        "from os.path import join\n"
        "from collections import defaultdict\n"
    )

    # 1. Test unique = True / ImportKey.ALIAS
    stream = io.StringIO(code)
    results = list(find_imports_in_stream(stream, unique=True))
    assert len(results) > 0

    stream = io.StringIO(code)
    results_alias = list(find_imports_in_stream(stream, unique=ImportKey.ALIAS))
    assert len(results_alias) > 0

    # 2. Test unique = ImportKey.ATTRIBUTE
    stream = io.StringIO(code)
    results_attr = list(find_imports_in_stream(stream, unique=ImportKey.ATTRIBUTE))
    assert len(results_attr) > 0

    # 3. Test unique = ImportKey.MODULE
    stream = io.StringIO(code)
    results_module = list(find_imports_in_stream(stream, unique=ImportKey.MODULE))
    assert len(results_module) > 0

    # 4. Test unique = ImportKey.PACKAGE
    stream = io.StringIO(code)
    results_pkg = list(find_imports_in_stream(stream, unique=ImportKey.PACKAGE))
    assert len(results_pkg) > 0


def test_find_imports_in_stream_with_seen_and_config():
    code = "import sys\n"
    stream = io.StringIO(code)
    # When unique=True, the key is the full import statement (e.g., "import sys\n" or "import sys").
    # Let's inspect what statement() returns or use unique=ImportKey.MODULE where key is "sys".
    stream = io.StringIO(code)
    results_mod = list(find_imports_in_stream(stream, unique=ImportKey.MODULE, _seen={"sys"}, line_length=80))
    assert len(results_mod) == 0

    # Also test when unique=True and we pre-seed with the exact statement
    stream = io.StringIO(code)
    import_obj = list(find_imports_in_stream(io.StringIO(code), unique=False))[0]
    stmt = import_obj.statement()
    stream = io.StringIO(code)
    results_true = list(find_imports_in_stream(stream, unique=True, _seen={stmt}, line_length=80))
    assert len(results_true) == 0
