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

    # Test unique = False (hits lines 560-561)
    stream = io.StringIO(code)
    imports_all = list(find_imports_in_stream(stream, unique=False))
    assert len(imports_all) > 0

    # Test unique = True / ImportKey.ALIAS (hits lines 565-566)
    stream = io.StringIO(code)
    imports_true = list(find_imports_in_stream(stream, unique=True))
    assert len(imports_true) > 0

    stream = io.StringIO(code)
    imports_alias = list(find_imports_in_stream(stream, unique=ImportKey.ALIAS))
    assert len(imports_alias) > 0

    # Test unique = ImportKey.ATTRIBUTE (hits lines 567-568)
    attr_code = """
from os import path
from os import path
from os import getcwd
"""
    stream = io.StringIO(attr_code)
    imports_attr = list(find_imports_in_stream(stream, unique=ImportKey.ATTRIBUTE))
    assert len(imports_attr) == 2

    # Test unique = ImportKey.MODULE (hits lines 569-570)
    mod_code = """
import os
import os
import sys
"""
    stream = io.StringIO(mod_code)
    imports_mod = list(find_imports_in_stream(stream, unique=ImportKey.MODULE))
    # os and os (repeated) and sys
    assert len(imports_mod) == 2

    # Test unique = ImportKey.PACKAGE (hits lines 571-572)
    pkg_code = """
import os.path
import os.environ
import sys.path
"""
    stream = io.StringIO(pkg_code)
    imports_pkg = list(find_imports_in_stream(stream, unique=ImportKey.PACKAGE))
    # os.path and os.environ both have package 'os', sys.path has 'sys'
    assert len(imports_pkg) == 2

    # Test with pre-populated _seen
    stream = io.StringIO("import os\nimport sys\n")
    imports_seen = list(find_imports_in_stream(stream, unique=True, _seen={"import os"}))
    statements = [i.statement() for i in imports_seen]
    assert "import os" not in statements
    assert "import sys" in statements
