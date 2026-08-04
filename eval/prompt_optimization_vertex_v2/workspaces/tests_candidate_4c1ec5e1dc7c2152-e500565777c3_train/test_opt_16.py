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
from os import path as p
from collections import defaultdict
from collections import OrderedDict
"""
    # 1. unique = True / ImportKey.ALIAS
    stream1 = io.StringIO(code)
    imports_true = list(find_imports_in_stream(stream1, unique=True))
    assert len(imports_true) > 0

    stream1_alias = io.StringIO(code)
    imports_alias = list(find_imports_in_stream(stream1_alias, unique=ImportKey.ALIAS))
    assert len(imports_alias) > 0

    # 2. unique = ImportKey.ATTRIBUTE
    stream2 = io.StringIO("from os import path\nfrom os import path\nfrom os import linesep\n")
    imports_attr = list(find_imports_in_stream(stream2, unique=ImportKey.ATTRIBUTE))
    assert len(imports_attr) == 2

    # 3. unique = ImportKey.MODULE
    stream3 = io.StringIO("import os.path\nimport os.path\nimport os.environ\n")
    imports_mod = list(find_imports_in_stream(stream3, unique=ImportKey.MODULE))
    assert len(imports_mod) >= 1

    # 4. unique = ImportKey.PACKAGE
    stream4 = io.StringIO("import os.path\nimport os.environ\nimport sys.version\n")
    imports_pkg = list(find_imports_in_stream(stream4, unique=ImportKey.PACKAGE))
    modules = [imp.module.split(".")[0] for imp in imports_pkg]
    assert "os" in modules
    assert "sys" in modules
    assert modules.count("os") == 1

    # 5. Test with an existing _seen set passed in using unique=True
    # For unique=True, key is import_statement(). Let's find out what statement() produces for "import os".
    stream_sample = io.StringIO("import os\n")
    sample_import = next(find_imports_in_stream(stream_sample))
    os_statement = sample_import.statement()

    stream5 = io.StringIO("import os\nimport sys\n")
    seen_set = {os_statement}
    imports_with_seen = list(find_imports_in_stream(stream5, unique=True, _seen=seen_set))
    modules_seen = [imp.module for imp in imports_with_seen]
    assert "os" not in modules_seen
    assert "sys" in modules_seen
