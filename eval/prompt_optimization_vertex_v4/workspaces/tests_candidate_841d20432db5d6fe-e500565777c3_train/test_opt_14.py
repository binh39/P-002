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
        "import collections.abc\n"
        "import collections.abc as cabc\n"
    )

    # Test unique=True (or ImportKey.ALIAS)
    stream = io.StringIO(code)
    imports_true = list(find_imports_in_stream(stream, unique=True))
    assert len(imports_true) > 0

    # Test unique=ImportKey.ALIAS
    stream = io.StringIO(code)
    imports_alias = list(find_imports_in_stream(stream, unique=ImportKey.ALIAS))
    assert len(imports_alias) > 0

    # Test unique=ImportKey.ATTRIBUTE
    stream = io.StringIO("from os import path\nfrom os import path\n")
    imports_attr = list(find_imports_in_stream(stream, unique=ImportKey.ATTRIBUTE))
    assert len(imports_attr) == 1

    # Test unique=ImportKey.MODULE
    stream2 = io.StringIO("import os\nimport os\nimport sys\n")
    imports_mod2 = list(find_imports_in_stream(stream2, unique=ImportKey.MODULE))
    assert len(imports_mod2) == 2

    # Test unique=ImportKey.PACKAGE
    stream3 = io.StringIO("import collections.abc\nimport collections.deque\nimport os\n")
    imports_pkg = list(find_imports_in_stream(stream3, unique=ImportKey.PACKAGE))
    packages = [imp.module.split(".")[0] for imp in imports_pkg]
    assert packages == ["collections", "os"]


def test_find_imports_in_stream_with_predefined_seen():
    code = "import os\nimport sys\n"
    # When unique=True, the key is the statement() string (e.g., "import os"), not just "os"
    seen = {"import os"}
    stream = io.StringIO(code)
    imports = list(find_imports_in_stream(stream, unique=True, _seen=seen))
    # 'import os' statement should be skipped because it's already in seen
    statements = [imp.statement() for imp in imports]
    assert "import os" not in statements
    assert "import sys" in statements
