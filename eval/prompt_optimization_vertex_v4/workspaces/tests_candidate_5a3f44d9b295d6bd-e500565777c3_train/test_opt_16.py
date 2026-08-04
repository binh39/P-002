# file: src\sample_repo\isort\isort\api.py:537-576
# asked: {"lines": [537, 538, 539, 540, 541, 542, 543, 544, 545, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [571, 574], [574, 564], [574, 575]]}
# gained: {"lines": [537, 540, 541, 542, 543, 556, 557, 558, 560, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [574, 564], [574, 575]]}

import io
from isort.api import find_imports_in_stream
from isort.api import ImportKey


def test_find_imports_in_stream_unique_variations():
    code = (
        "import os\n"
        "import os\n"
        "from os import path\n"
        "from os import path as p\n"
        "from collections import defaultdict\n"
        "from collections.abc import Mapping\n"
    )

    # Test unique=True / ImportKey.ALIAS
    stream1 = io.StringIO(code)
    imports_alias = list(find_imports_in_stream(stream1, unique=True))
    assert len(imports_alias) > 0

    stream1_alt = io.StringIO(code)
    imports_enum_alias = list(find_imports_in_stream(stream1_alt, unique=ImportKey.ALIAS))
    assert len(imports_enum_alias) == len(imports_alias)

    # Test unique=ImportKey.ATTRIBUTE
    stream2 = io.StringIO(code)
    imports_attr = list(find_imports_in_stream(stream2, unique=ImportKey.ATTRIBUTE))
    assert len(imports_attr) > 0

    # Test unique=ImportKey.MODULE
    stream3 = io.StringIO(code)
    imports_module = list(find_imports_in_stream(stream3, unique=ImportKey.MODULE))
    assert len(imports_module) > 0

    # Test unique=ImportKey.PACKAGE
    stream4 = io.StringIO(code)
    imports_package = list(find_imports_in_stream(stream4, unique=ImportKey.PACKAGE))
    assert len(imports_package) > 0

    # Test with existing _seen set passed in
    stream5 = io.StringIO("import os\nimport sys\n")
    # For `import os`, the key when unique=True is `import os` (the statement), not "os".
    # So we pass the statement string in `_seen`.
    seen_set = {"import os"}
    imports_with_seen = list(find_imports_in_stream(stream5, unique=True, _seen=seen_set))
    statements = [imp.statement() for imp in imports_with_seen]
    assert "import os" not in statements
    assert "import sys" in statements
