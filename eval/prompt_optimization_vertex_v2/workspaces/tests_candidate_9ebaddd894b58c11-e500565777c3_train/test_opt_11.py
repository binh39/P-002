# file: src\sample_repo\isort\isort\api.py:537-576
# asked: {"lines": [537, 538, 539, 540, 541, 542, 543, 544, 545, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [571, 574], [574, 564], [574, 575]]}
# gained: {"lines": [537, 540, 541, 542, 543, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [574, 564], [574, 575]]}

import io
from isort.api import find_imports_in_stream, ImportKey

def test_find_imports_in_stream_unique_variations():
    code = """
import os
import os
import sys
from os import path
from os import path as os_path
from collections import defaultdict
"""

    # Test unique=False (default or explicit False)
    stream = io.StringIO(code)
    imports_false = list(find_imports_in_stream(stream, unique=False))
    assert len(imports_false) > 0

    # Test unique=True (or ImportKey.ALIAS)
    stream = io.StringIO(code)
    imports_true = list(find_imports_in_stream(stream, unique=True))
    assert len(imports_true) > 0

    # Test unique=ImportKey.ALIAS
    stream = io.StringIO(code)
    imports_alias = list(find_imports_in_stream(stream, unique=ImportKey.ALIAS))
    assert len(imports_alias) > 0

    # Test unique=ImportKey.ATTRIBUTE
    stream = io.StringIO("from os import path\nfrom os import path\nfrom os import listdir\n")
    imports_attr = list(find_imports_in_stream(stream, unique=ImportKey.ATTRIBUTE))
    assert len(imports_attr) == 2

    # Test unique=ImportKey.MODULE
    stream = io.StringIO("import os.path\nimport os.path\nimport os.path\n")
    imports_mod = list(find_imports_in_stream(stream, unique=ImportKey.MODULE))
    assert len(imports_mod) == 1

    # Test unique=ImportKey.PACKAGE
    stream = io.StringIO("import os.path\nimport os.environ\nimport sys.path\n")
    imports_pkg = list(find_imports_in_stream(stream, unique=ImportKey.PACKAGE))
    assert len(imports_pkg) == 2

    # Test with _seen provided
    stream = io.StringIO("import os\n")
    seen = set()
    imports_seen = list(find_imports_in_stream(stream, unique=True, _seen=seen))
    assert len(imports_seen) == 1
