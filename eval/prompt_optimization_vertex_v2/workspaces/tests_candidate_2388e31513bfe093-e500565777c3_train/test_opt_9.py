# file: src\sample_repo\isort\isort\api.py:537-576
# asked: {"lines": [537, 538, 539, 540, 541, 542, 543, 544, 545, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [571, 574], [574, 564], [574, 575]]}
# gained: {"lines": [537, 540, 541, 542, 543, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [574, 564], [574, 575]]}

import io
from isort.api import find_imports_in_stream, ImportKey


def test_find_imports_in_stream_not_unique():
    code = "import os\nimport os\nimport sys"
    stream = io.StringIO(code)
    imports = list(find_imports_in_stream(stream, unique=False))
    # When unique is False, it yields all identified imports directly via "if not unique:"
    assert len(imports) == 3


def test_find_imports_in_stream_unique_true_and_alias():
    code = "import os\nimport os\nimport sys as s\nimport sys as s"
    stream = io.StringIO(code)
    # unique=True or unique=ImportKey.ALIAS uses identified_import.statement()
    imports_true = list(find_imports_in_stream(io.StringIO(code), unique=True))
    imports_alias = list(
        find_imports_in_stream(io.StringIO(code), unique=ImportKey.ALIAS)
    )
    assert len(imports_true) == 2
    assert len(imports_alias) == 2


def test_find_imports_in_stream_unique_attribute():
    code = "from os import path\nfrom os import path\nfrom sys import argv"
    stream = io.StringIO(code)
    imports = list(
        find_imports_in_stream(stream, unique=ImportKey.ATTRIBUTE)
    )
    # Keys will be "os.path", "os.path", "sys.argv" -> deduplicated to "os.path", "sys.argv"
    assert len(imports) == 2


def test_find_imports_in_stream_unique_module():
    code = "from os import path\nfrom os import environ\nfrom sys import argv"
    stream = io.StringIO(code)
    imports = list(find_imports_in_stream(stream, unique=ImportKey.MODULE))
    # Keys will be "os", "os", "sys" -> deduplicated to "os", "sys"
    assert len(imports) == 2


def test_find_imports_in_stream_unique_package():
    code = "from os.path import join\nfrom os.environ import get\nfrom sys import argv"
    stream = io.StringIO(code)
    imports = list(find_imports_in_stream(stream, unique=ImportKey.PACKAGE))
    # Keys will be "os", "os", "sys" -> deduplicated to "os", "sys"
    assert len(imports) == 2


def test_find_imports_in_stream_with_seen_set():
    code = "import os\nimport sys"
    stream = io.StringIO(code)
    seen = {"import os"}
    imports = list(
        find_imports_in_stream(stream, unique=True, _seen=seen)
    )
    # "import os" is already in seen, so only "sys" should be returned
    assert len(imports) == 1
    assert imports[0].module == "sys"
