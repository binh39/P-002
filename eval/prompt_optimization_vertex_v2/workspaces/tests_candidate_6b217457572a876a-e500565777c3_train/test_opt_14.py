# file: src\sample_repo\isort\isort\api.py:537-576
# asked: {"lines": [537, 538, 539, 540, 541, 542, 543, 544, 545, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [571, 574], [574, 564], [574, 575]]}
# gained: {"lines": [537, 540, 541, 542, 543, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [574, 564], [574, 575]]}

import io
from isort.api import find_imports_in_stream, ImportKey


def test_find_imports_in_stream_not_unique():
    code = "import os\nimport os\nfrom sys import path\n"
    stream = io.StringIO(code)
    imports = list(find_imports_in_stream(stream, unique=False))
    # Should yield all imports without filtering
    assert len(imports) == 3


def test_find_imports_in_stream_unique_true_and_alias():
    code = "import os\nimport os\nfrom sys import path\n"
    
    # unique=True
    stream = io.StringIO(code)
    imports_true = list(find_imports_in_stream(stream, unique=True))
    assert len(imports_true) == 2

    # unique=ImportKey.ALIAS
    stream = io.StringIO(code)
    imports_alias = list(find_imports_in_stream(stream, unique=ImportKey.ALIAS))
    assert len(imports_alias) == 2


def test_find_imports_in_stream_unique_attribute():
    code = "from os import path\nfrom os import path\nfrom os import environ\n"
    stream = io.StringIO(code)
    imports = list(find_imports_in_stream(stream, unique=ImportKey.ATTRIBUTE))
    # os.path appears twice, os.environ once -> 2 unique attributes
    assert len(imports) == 2


def test_find_imports_in_stream_unique_module():
    code = "from os.path import join\nfrom os.path import split\nfrom sys import path\n"
    stream = io.StringIO(code)
    imports = list(find_imports_in_stream(stream, unique=ImportKey.MODULE))
    # os.path (twice under same module), sys.path -> 2 unique modules
    assert len(imports) == 2


def test_find_imports_in_stream_unique_package():
    code = "from os.path import join\nfrom os.environ import get\nfrom sys import path\n"
    stream = io.StringIO(code)
    imports = list(find_imports_in_stream(stream, unique=ImportKey.PACKAGE))
    # os.path and os.environ share package 'os', sys has package 'sys' -> 2 unique packages
    assert len(imports) == 2


def test_find_imports_in_stream_with_pre_seen():
    code = "import os\nimport sys\n"
    stream = io.StringIO(code)
    # When unique=True, statement() for "import os" returns "import os"
    seen = {"import os"}
    imports = list(find_imports_in_stream(stream, unique=True, _seen=seen))
    assert len(imports) == 1
    assert imports[0].module == "sys"
