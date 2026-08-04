# file: src\sample_repo\isort\isort\api.py:537-576
# asked: {"lines": [537, 538, 539, 540, 541, 542, 543, 544, 545, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [571, 574], [574, 564], [574, 575]]}
# gained: {"lines": [537, 540, 541, 542, 543, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [574, 564], [574, 575]]}

from io import StringIO
from isort.api import find_imports_in_stream
from isort.api import ImportKey


def test_find_imports_in_stream_not_unique():
    content = "import os\nimport sys\nimport os\n"
    stream = StringIO(content)
    imports = list(find_imports_in_stream(stream, unique=False))
    assert len(imports) == 3


def test_find_imports_in_stream_unique_true_and_alias():
    for unique_val in (True, ImportKey.ALIAS):
        content = "import os\nimport os\nfrom sys import path\n"
        stream = StringIO(content)
        imports = list(find_imports_in_stream(stream, unique=unique_val))
        statements = [imp.statement() for imp in imports]
        assert statements == ["import os", "from sys import path"]


def test_find_imports_in_stream_unique_attribute():
    content = "import os.path\nimport os.path\nimport sys.path\n"
    stream = StringIO(content)
    imports = list(find_imports_in_stream(stream, unique=ImportKey.ATTRIBUTE))
    assert len(imports) == 2


def test_find_imports_in_stream_unique_module():
    content = "import os\nimport os\nimport sys\n"
    stream = StringIO(content)
    imports = list(find_imports_in_stream(stream, unique=ImportKey.MODULE))
    modules = [imp.module for imp in imports]
    assert modules == ["os", "sys"]


def test_find_imports_in_stream_unique_package():
    content = "import os.path\nimport os.environ\nimport sys.path\n"
    stream = StringIO(content)
    imports = list(find_imports_in_stream(stream, unique=ImportKey.PACKAGE))
    packages = [imp.module.split(".")[0] for imp in imports]
    assert packages == ["os", "sys"]


def test_find_imports_in_stream_with_seen_and_config():
    content = "import os\nimport sys\n"
    stream = StringIO(content)
    seen = {"import os"}
    imports = list(find_imports_in_stream(stream, unique=True, _seen=seen))
    assert len(imports) == 1
    assert imports[0].statement() == "import sys"
