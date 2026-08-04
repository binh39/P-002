# file: src\sample_repo\isort\isort\api.py:537-576
# asked: {"lines": [537, 538, 539, 540, 541, 542, 543, 544, 545, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [571, 574], [574, 564], [574, 575]]}
# gained: {"lines": [537, 540, 541, 542, 543, 556, 557, 558, 560, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [574, 564], [574, 575]]}

from io import StringIO
from isort.api import find_imports_in_stream, ImportKey

def test_find_imports_in_stream_unique_modes():
    content = "import os\nimport os\nfrom sys import path, version\nfrom sys import version as v\nimport os.path\n"
    
    # Test unique=True (ALIAS) and _seen provided
    stream1 = StringIO(content)
    seen_set = set()
    imports_true = list(find_imports_in_stream(stream1, unique=True, _seen=seen_set))
    assert len(imports_true) > 0

    # Test unique=ImportKey.ALIAS
    stream2 = StringIO(content)
    imports_alias = list(find_imports_in_stream(stream2, unique=ImportKey.ALIAS))
    assert len(imports_alias) > 0

    # Test unique=ImportKey.ATTRIBUTE
    stream3 = StringIO(content)
    imports_attr = list(find_imports_in_stream(stream3, unique=ImportKey.ATTRIBUTE))
    assert len(imports_attr) > 0

    # Test unique=ImportKey.MODULE
    stream4 = StringIO(content)
    imports_mod = list(find_imports_in_stream(stream4, unique=ImportKey.MODULE))
    assert len(imports_mod) > 0

    # Test unique=ImportKey.PACKAGE
    stream5 = StringIO(content)
    imports_pkg = list(find_imports_in_stream(stream5, unique=ImportKey.PACKAGE))
    assert len(imports_pkg) > 0
