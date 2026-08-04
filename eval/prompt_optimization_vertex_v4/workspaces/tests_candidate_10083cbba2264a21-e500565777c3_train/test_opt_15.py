# file: src\sample_repo\isort\isort\api.py:537-576
# asked: {"lines": [537, 538, 539, 540, 541, 542, 543, 544, 545, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [571, 574], [574, 564], [574, 575]]}
# gained: {"lines": [537, 540, 541, 542, 543, 556, 557, 558, 560, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [574, 564], [574, 575]]}

import io
from isort.api import find_imports_in_stream, ImportKey

def test_find_imports_in_stream_unique_modes():
    code = (
        "import os\n"
        "import os\n"
        "import sys\n"
        "from os import path\n"
        "from os import path as p\n"
    )

    # Test unique=True / ImportKey.ALIAS / duplicate filtering / key handling
    stream1 = io.StringIO(code)
    imports_alias = list(find_imports_in_stream(stream1, unique=ImportKey.ALIAS))
    assert len(imports_alias) > 0

    stream2 = io.StringIO(code)
    imports_true = list(find_imports_in_stream(stream2, unique=True))
    assert len(imports_true) > 0

    # Test unique=ImportKey.ATTRIBUTE
    attr_code = (
        "import os.path\n"
        "import os.path\n"
        "import sys\n"
    )
    stream3 = io.StringIO(attr_code)
    imports_attr = list(find_imports_in_stream(stream3, unique=ImportKey.ATTRIBUTE))
    assert len(imports_attr) > 0

    # Test unique=ImportKey.MODULE
    stream4 = io.StringIO(code)
    imports_module = list(find_imports_in_stream(stream4, unique=ImportKey.MODULE))
    assert len(imports_module) > 0

    # Test unique=ImportKey.PACKAGE and custom _seen
    stream5 = io.StringIO(code)
    seen = set()
    imports_pkg = list(find_imports_in_stream(stream5, unique=ImportKey.PACKAGE, _seen=seen))
    assert len(imports_pkg) > 0
