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
        "import sys\n"
        "import sys\n"
    )

    # unique = False (already covered or part of main path)
    stream = io.StringIO(code)
    imports_false = list(find_imports_in_stream(stream, unique=False))
    assert len(imports_false) == 6

    # unique = True (or ImportKey.ALIAS)
    stream = io.StringIO(code)
    imports_true = list(find_imports_in_stream(stream, unique=True))
    statements = [imp.statement() for imp in imports_true]
    # Should de-duplicate identical statements
    assert len(imports_true) < 6

    # unique = ImportKey.ALIAS
    stream = io.StringIO(code)
    imports_alias = list(find_imports_in_stream(stream, unique=ImportKey.ALIAS))
    assert len(imports_alias) == len(imports_true)

    # unique = ImportKey.ATTRIBUTE
    code_attr = (
        "from os import path\n"
        "from os import path\n"
        "from os import getcwd\n"
    )
    stream = io.StringIO(code_attr)
    imports_attr = list(find_imports_in_stream(stream, unique=ImportKey.ATTRIBUTE))
    assert len(imports_attr) == 2

    # unique = ImportKey.MODULE
    code_mod = (
        "import os.path\n"
        "import os.path\n"
        "import os.environ\n"
    )
    stream = io.StringIO(code_mod)
    imports_mod = list(find_imports_in_stream(stream, unique=ImportKey.MODULE))
    # os.path and os.environ share module 'os' if structured a certain way, or let's test distinct modules
    code_mod2 = (
        "import os.path\n"
        "import os.path\n"
        "import sys.version\n"
    )
    stream = io.StringIO(code_mod2)
    imports_mod2 = list(find_imports_in_stream(stream, unique=ImportKey.MODULE))
    # os.path module is 'os.path', sys.version module is 'sys.version'
    assert len(imports_mod2) == 2

    # unique = ImportKey.PACKAGE
    code_pkg = (
        "import os.path\n"
        "import os.environ\n"
        "import sys.version\n"
    )
    stream = io.StringIO(code_pkg)
    imports_pkg = list(find_imports_in_stream(stream, unique=ImportKey.PACKAGE, _seen=set()))
    # os.path and os.environ share package 'os', sys.version package is 'sys'
    assert len(imports_pkg) == 2
