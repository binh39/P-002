# file: src\sample_repo\isort\isort\api.py:537-576
# asked: {"lines": [537, 538, 539, 540, 541, 542, 543, 544, 545, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [571, 574], [574, 564], [574, 575]]}
# gained: {"lines": [537, 540, 541, 542, 543, 556, 557, 558, 560, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [574, 564], [574, 575]]}

import io
from isort.api import find_imports_in_stream, ImportKey

def test_find_imports_in_stream_unique_modes():
    code = (
        "import os\n"
        "import os\n"
        "import os.path\n"
        "from sys import version as v1\n"
        "from sys import version as v2\n"
        "from collections.abc import Iterator\n"
    )

    # Test unique=True / ImportKey.ALIAS
    stream = io.StringIO(code)
    imports_alias = list(find_imports_in_stream(stream, unique=True))
    assert len(imports_alias) > 0

    # Test ImportKey.ATTRIBUTE
    stream = io.StringIO(code)
    imports_attr = list(find_imports_in_stream(stream, unique=ImportKey.ATTRIBUTE))
    assert len(imports_attr) > 0

    # Test ImportKey.MODULE
    stream = io.StringIO(code)
    imports_mod = list(find_imports_in_stream(stream, unique=ImportKey.MODULE))
    assert len(imports_mod) > 0

    # Test ImportKey.PACKAGE
    stream = io.StringIO(code)
    imports_pkg = list(find_imports_in_stream(stream, unique=ImportKey.PACKAGE))
    assert len(imports_pkg) > 0

    # Test with existing _seen set
    stream = io.StringIO("import os\nimport sys\n")
    seen_set = set()
    imports_seen = list(find_imports_in_stream(stream, unique=ImportKey.MODULE, _seen=seen_set))
    assert len(imports_seen) > 0
