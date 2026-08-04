# file: src\sample_repo\isort\isort\api.py:537-576
# asked: {"lines": [537, 538, 539, 540, 541, 542, 543, 544, 545, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [571, 574], [574, 564], [574, 575]]}
# gained: {"lines": [537, 540, 541, 542, 543, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [574, 564], [574, 575]]}

import io
from isort.api import find_imports_in_stream, ImportKey

def test_find_imports_in_stream_not_unique():
    code = "import os\nimport os\n"
    stream = io.StringIO(code)
    imports = list(find_imports_in_stream(stream, unique=False))
    # When unique=False, it should yield all identified imports without filtering
    assert len(imports) == 2

def test_find_imports_in_stream_unique_true_and_alias():
    code = "import os\nimport os\nimport sys as s\nimport sys as s\n"
    
    # Test unique=True
    stream = io.StringIO(code)
    imports_true = list(find_imports_in_stream(stream, unique=True))
    assert len(imports_true) == 2

    # Test unique=ImportKey.ALIAS
    stream = io.StringIO(code)
    imports_alias = list(find_imports_in_stream(stream, unique=ImportKey.ALIAS))
    assert len(imports_alias) == 2

def test_find_imports_in_stream_unique_attribute():
    code = "from os import path\nfrom os import path\nfrom os import name\n"
    stream = io.StringIO(code)
    imports = list(find_imports_in_stream(stream, unique=ImportKey.ATTRIBUTE))
    # 'os.path' appears twice, 'os.name' once
    assert len(imports) == 2

def test_find_imports_in_stream_unique_module():
    code = "from os import path\nfrom os import environ\nimport sys\n"
    stream = io.StringIO(code)
    imports = list(find_imports_in_stream(stream, unique=ImportKey.MODULE))
    # 'os' module appears twice, 'sys' once
    assert len(imports) == 2

def test_find_imports_in_stream_unique_package_and_seen():
    code = "from package_a.sub import foo\nfrom package_a.other import bar\nimport package_b\n"
    stream = io.StringIO(code)
    seen = {"package_b"}
    imports = list(find_imports_in_stream(stream, unique=ImportKey.PACKAGE, _seen=seen))
    # package_a.sub -> package_a (first)
    # package_a.other -> package_a (seen, skipped)
    # package_b -> already in initial _seen set (skipped)
    assert len(imports) == 1
    assert imports[0].module.startswith("package_a")
