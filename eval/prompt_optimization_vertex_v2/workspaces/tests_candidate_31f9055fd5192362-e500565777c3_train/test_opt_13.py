# file: src\sample_repo\isort\isort\api.py:537-576
# asked: {"lines": [537, 538, 539, 540, 541, 542, 543, 544, 545, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [571, 574], [574, 564], [574, 575]]}
# gained: {"lines": [537, 540, 541, 542, 543, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [574, 564], [574, 575]]}

import io
from isort.api import find_imports_in_stream, ImportKey


def test_find_imports_in_stream_unique_false():
    code = "import os\nimport os\n"
    stream = io.StringIO(code)
    imports = list(find_imports_in_stream(stream, unique=False))
    assert len(imports) == 2


def test_find_imports_in_stream_unique_true():
    code = "import os\nimport os\nimport sys\n"
    stream = io.StringIO(code)
    imports = list(find_imports_in_stream(stream, unique=True))
    assert len(imports) == 2
    assert [imp.statement() for imp in imports] == ["import os", "import sys"]


def test_find_imports_in_stream_unique_alias():
    code = "import os\nimport os\n"
    stream = io.StringIO(code)
    imports = list(find_imports_in_stream(stream, unique=ImportKey.ALIAS))
    assert len(imports) == 1


def test_find_imports_in_stream_unique_attribute():
    code = "from os import path\nfrom os import path\nfrom os import name\n"
    stream = io.StringIO(code)
    imports = list(find_imports_in_stream(stream, unique=ImportKey.ATTRIBUTE))
    assert len(imports) == 2


def test_find_imports_in_stream_unique_module():
    code = "from os import path\nfrom os import name\nfrom sys import version\n"
    stream = io.StringIO(code)
    imports = list(find_imports_in_stream(stream, unique=ImportKey.MODULE))
    assert len(imports) == 2


def test_find_imports_in_stream_unique_package():
    code = "import os.path\nimport os.name\nimport sys\n"
    stream = io.StringIO(code)
    imports = list(find_imports_in_stream(stream, unique=ImportKey.PACKAGE))
    assert len(imports) == 2


def test_find_imports_in_stream_with_seen_passed():
    code = "import os\nimport sys\n"
    stream = io.StringIO(code)
    seen = {"os"}
    imports = list(find_imports_in_stream(stream, unique=ImportKey.MODULE, _seen=seen))
    assert len(imports) == 1
    assert imports[0].module == "sys"
