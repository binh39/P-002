# file: src\sample_repo\isort\isort\api.py:537-576
# asked: {"lines": [537, 538, 539, 540, 541, 542, 543, 544, 545, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [571, 574], [574, 564], [574, 575]]}
# gained: {"lines": [537, 540, 541, 542, 543, 556, 557, 558, 560, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [574, 564], [574, 575]]}

import io
from isort.api import find_imports_in_stream, ImportKey
from isort.settings import Config


def test_find_imports_in_stream_unique_variations():
    code = (
        "import os\n"
        "import os\n"
        "from os import path\n"
        "from os import path as p\n"
        "import os.path\n"
        "import sys\n"
    )

    # Test unique = True / ImportKey.ALIAS
    stream1 = io.StringIO(code)
    imports1 = list(find_imports_in_stream(stream1, unique=True))
    assert len(imports1) > 0

    stream1_alias = io.StringIO(code)
    imports1_alias = list(find_imports_in_stream(stream1_alias, unique=ImportKey.ALIAS))
    assert len(imports1_alias) > 0

    # Test unique = ImportKey.ATTRIBUTE
    code_attr = "from os import path\nfrom os import path\nfrom os import name\n"
    stream2 = io.StringIO(code_attr)
    imports2 = list(find_imports_in_stream(stream2, unique=ImportKey.ATTRIBUTE))
    assert len(imports2) == 2

    # Test unique = ImportKey.MODULE
    code_mod = "import os\nimport os\nimport sys\n"
    stream3 = io.StringIO(code_mod)
    imports3 = list(find_imports_in_stream(stream3, unique=ImportKey.MODULE))
    assert len(imports3) == 2

    # Test unique = ImportKey.PACKAGE
    code_pkg = "import os.path\nimport os.environ\nimport sys.version\n"
    stream4 = io.StringIO(code_pkg)
    imports4 = list(find_imports_in_stream(stream4, unique=ImportKey.PACKAGE))
    # os.path and os.environ share package 'os', sys.version has package 'sys'
    assert len(imports4) == 2

    # Test with _seen provided
    stream5 = io.StringIO("import os\nimport sys\n")
    seen_set = {"import os"}
    imports5 = list(find_imports_in_stream(stream5, unique=True, _seen=seen_set))
    # statement 'import os' should be skipped because it's already in seen_set
    statements = [imp.statement() for imp in imports5]
    assert "import os" not in statements
    assert "import sys" in statements
