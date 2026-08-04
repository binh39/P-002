# file: src\sample_repo\isort\isort\api.py:537-576
# asked: {"lines": [537, 538, 539, 540, 541, 542, 543, 544, 545, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [571, 574], [574, 564], [574, 575]]}
# gained: {"lines": [537, 540, 541, 542, 543, 556, 557, 558, 560, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [574, 564], [574, 575]]}

from io import StringIO
from isort.api import find_imports_in_stream, ImportKey


def test_find_imports_in_stream_unique_true_and_alias():
    code = "import os\nimport os\nfrom sys import path as p1, path as p2"
    stream = StringIO(code)
    
    # unique = True
    imports_true = list(find_imports_in_stream(stream, unique=True))
    assert len(imports_true) == 3

    # unique = ImportKey.ALIAS
    stream = StringIO(code)
    imports_alias = list(find_imports_in_stream(stream, unique=ImportKey.ALIAS))
    assert len(imports_alias) == 3


def test_find_imports_in_stream_unique_attribute():
    code = "from os import path\nfrom os import path\nfrom sys import path"
    stream = StringIO(code)
    imports = list(find_imports_in_stream(stream, unique=ImportKey.ATTRIBUTE))
    # os.path appears twice, second should be skipped
    assert len(imports) == 2
    assert imports[0].attribute == "path"


def test_find_imports_in_stream_unique_module():
    code = "from os import path\nfrom os import environ\nimport sys"
    stream = StringIO(code)
    imports = list(find_imports_in_stream(stream, unique=ImportKey.MODULE))
    # from os import path and from os import environ share module 'os'
    assert len(imports) == 2
    assert imports[0].module == "os"
    assert imports[1].module == "sys"


def test_find_imports_in_stream_unique_package():
    code = "import package_a.sub.mod1\nimport package_a.sub.mod2\nimport package_b"
    stream = StringIO(code)
    imports = list(find_imports_in_stream(stream, unique=ImportKey.PACKAGE))
    # package_a.sub.mod1 and package_a.sub.mod2 share package 'package_a'
    assert len(imports) == 2
    assert imports[0].module.split(".")[0] == "package_a"
    assert imports[1].module.split(".")[0] == "package_b"


def test_find_imports_in_stream_with_seen():
    code = "import os\nimport sys"
    stream = StringIO(code)
    seen = {"import os"}
    imports = list(find_imports_in_stream(stream, unique=True, _seen=seen))
    # 'import os' statement is already in seen, so only sys should be returned
    assert len(imports) == 1
    assert imports[0].module == "sys"
