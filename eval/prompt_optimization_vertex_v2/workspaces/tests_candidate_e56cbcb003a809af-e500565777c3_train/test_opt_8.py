# file: src\sample_repo\isort\isort\api.py:537-576
# asked: {"lines": [537, 538, 539, 540, 541, 542, 543, 544, 545, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [571, 574], [574, 564], [574, 575]]}
# gained: {"lines": [537, 540, 541, 542, 543, 556, 557, 558, 560, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [574, 564], [574, 575]]}

import io
from isort.api import find_imports_in_stream, ImportKey

def test_find_imports_in_stream_unique_options():
    code = (
        "import os\n"
        "import os\n"
        "from sys import path\n"
        "from sys import version\n"
        "import collections.abc\n"
        "import collections.defaultdict\n"
    )

    # Test unique=True (or ImportKey.ALIAS)
    stream = io.StringIO(code)
    imports_alias = list(find_imports_in_stream(stream, unique=True))
    assert len(imports_alias) == 5  # "import os" is duplicated, others are unique

    stream = io.StringIO(code)
    imports_enum_alias = list(find_imports_in_stream(stream, unique=ImportKey.ALIAS))
    assert len(imports_enum_alias) == 5

    # Test unique=ImportKey.ATTRIBUTE
    code_attr = (
        "from os import path\n"
        "from os import path\n"
        "from os import environ\n"
    )
    stream = io.StringIO(code_attr)
    imports_attr = list(find_imports_in_stream(stream, unique=ImportKey.ATTRIBUTE))
    assert len(imports_attr) == 2

    # Test unique=ImportKey.MODULE
    code_mod = (
        "import os.path\n"
        "import os.path\n"
        "import os.environ\n"
    )
    stream = io.StringIO(code_mod)
    imports_mod = list(find_imports_in_stream(stream, unique=ImportKey.MODULE))
    assert len(imports_mod) == 2

    # Test unique=ImportKey.PACKAGE
    code_pkg = (
        "import os.path\n"
        "import os.environ\n"
        "import sys.path\n"
    )
    stream = io.StringIO(code_pkg)
    imports_pkg = list(find_imports_in_stream(stream, unique=ImportKey.PACKAGE))
    # os.path and os.environ share package 'os', sys.path is 'sys'
    assert len(imports_pkg) == 2

    # Test with existing _seen set
    stream = io.StringIO("import os\nimport sys\n")
    seen = set()
    imports_seen = list(find_imports_in_stream(stream, unique=True, _seen=seen))
    assert len(imports_seen) == 2
    assert "import os" in seen
