# file: src\sample_repo\isort\isort\api.py:537-576
# asked: {"lines": [537, 538, 539, 540, 541, 542, 543, 544, 545, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [571, 574], [574, 564], [574, 575]]}
# gained: {"lines": [537, 540, 541, 542, 543, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [574, 564], [574, 575]]}

import io
from isort.api import find_imports_in_stream, ImportKey

def test_find_imports_in_stream_unique_variations():
    code = (
        "import os\n"
        "import os\n"
        "from os import path\n"
        "from os import path as p\n"
        "import sys.path\n"
        "import sys.version\n"
    )

    # unique = False (default)
    stream = io.StringIO(code)
    imports_false = list(find_imports_in_stream(stream, unique=False))
    assert len(imports_false) == 6

    # unique = True / ImportKey.ALIAS
    stream = io.StringIO(code)
    imports_true = list(find_imports_in_stream(stream, unique=True))
    # 'import os' appears twice, second should be deduplicated
    assert len(imports_true) == 5

    stream = io.StringIO(code)
    imports_alias = list(find_imports_in_stream(stream, unique=ImportKey.ALIAS))
    assert len(imports_alias) == 5

    # unique = ImportKey.ATTRIBUTE
    # sys.path and sys.version have attributes 'path' and 'version'
    code_attr = (
        "import sys.path\n"
        "import sys.path\n"
    )
    stream = io.StringIO(code_attr)
    imports_attr = list(find_imports_in_stream(stream, unique=ImportKey.ATTRIBUTE))
    assert len(imports_attr) == 1

    # unique = ImportKey.MODULE
    code_mod = (
        "from os import path\n"
        "from os import getcwd\n"
    )
    stream = io.StringIO(code_mod)
    imports_mod = list(find_imports_in_stream(stream, unique=ImportKey.MODULE))
    # both share module 'os'
    assert len(imports_mod) == 1

    # unique = ImportKey.PACKAGE
    code_pkg = (
        "import os.path\n"
        "import os.environ\n"
    )
    stream = io.StringIO(code_pkg)
    imports_pkg = list(find_imports_in_stream(stream, unique=ImportKey.PACKAGE))
    # both share package 'os'
    assert len(imports_pkg) == 1

    # test with existing _seen set
    stream = io.StringIO("import os\n")
    seen_set = {"import os"}
    imports_with_seen = list(find_imports_in_stream(stream, unique=True, _seen=seen_set))
    assert len(imports_with_seen) == 0
