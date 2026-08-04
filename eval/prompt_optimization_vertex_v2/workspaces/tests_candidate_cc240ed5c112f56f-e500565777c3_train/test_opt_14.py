# file: src\sample_repo\isort\isort\api.py:537-576
# asked: {"lines": [537, 538, 539, 540, 541, 542, 543, 544, 545, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [571, 574], [574, 564], [574, 575]]}
# gained: {"lines": [537, 540, 541, 542, 543, 556, 557, 558, 560, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [574, 564], [574, 575]]}

import io
from isort.api import find_imports_in_stream
from isort.api import ImportKey


def test_find_imports_in_stream_unique_true():
    code = "import os\nimport os\nfrom sys import path\n"
    stream = io.StringIO(code)
    imports = list(find_imports_in_stream(stream, unique=True))
    statements = [imp.statement() for imp in imports]
    # Duplicates should be filtered out
    assert statements.count("import os") == 1


def test_find_imports_in_stream_unique_alias():
    code = "import os\nimport os\n"
    stream = io.StringIO(code)
    imports = list(find_imports_in_stream(stream, unique=ImportKey.ALIAS))
    assert len(imports) == 1


def test_find_imports_in_stream_unique_attribute():
    code = "from os import path\nfrom os import path\nfrom os import name\n"
    stream = io.StringIO(code)
    imports = list(find_imports_in_stream(stream, unique=ImportKey.ATTRIBUTE))
    # Should have 'os.path' and 'os.name'
    assert len(imports) == 2


def test_find_imports_in_stream_unique_module():
    code = "from os.path import join\nfrom os.path import split\nfrom sys import path\n"
    stream = io.StringIO(code)
    imports = list(find_imports_in_stream(stream, unique=ImportKey.MODULE))
    # Should keep one from os.path and one from sys
    modules = {imp.module for imp in imports}
    assert modules == {"os.path", "sys"}


def test_find_imports_in_stream_unique_package():
    code = "from os.path import join\nfrom os.environ import get\nfrom sys import path\n"
    stream = io.StringIO(code)
    imports = list(find_imports_in_stream(stream, unique=ImportKey.PACKAGE))
    # os.path and os.environ share the package 'os', sys has package 'sys'
    packages = {imp.module.split(".")[0] for imp in imports}
    assert packages == {"os", "sys"}
    assert len(imports) == 2


def test_find_imports_in_stream_with_seen_arg():
    code = "import os\nimport sys\n"
    stream = io.StringIO(code)
    seen = {"os"}
    # Using unique=ImportKey.MODULE so 'key' is import.module
    imports = list(find_imports_in_stream(stream, unique=ImportKey.MODULE, _seen=seen))
    modules = {imp.module for imp in imports}
    assert "os" not in modules
    assert "sys" in modules
