# file: src\sample_repo\isort\isort\api.py:537-576
# asked: {"lines": [537, 538, 539, 540, 541, 542, 543, 544, 545, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [571, 574], [574, 564], [574, 575]]}
# gained: {"lines": [537, 540, 541, 542, 543, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 574, 575, 576], "branches": [[560, 561], [560, 563], [564, 0], [564, 565], [565, 566], [565, 567], [567, 568], [567, 569], [569, 570], [569, 571], [571, 572], [574, 564], [574, 575]]}

import io
from isort.api import find_imports_in_stream, ImportKey
from isort.settings import Config

def test_find_imports_in_stream_unique_variations():
    code = (
        "import os\n"
        "import os\n"
        "from os import path\n"
        "from os import path as p\n"
        "import sys\n"
    )

    # Test unique=False (covered by lines 560-561)
    stream = io.StringIO(code)
    imports_false = list(find_imports_in_stream(stream, unique=False))
    assert len(imports_false) == 5

    # Test unique=True / ImportKey.ALIAS (covered by lines 565-566)
    stream = io.StringIO(code)
    imports_true = list(find_imports_in_stream(stream, unique=True))
    assert len(imports_true) == 4

    stream = io.StringIO(code)
    imports_alias = list(find_imports_in_stream(stream, unique=ImportKey.ALIAS))
    assert len(imports_alias) == 4

    # Test unique=ImportKey.ATTRIBUTE (covered by lines 567-568)
    attr_code = (
        "from os import path\n"
        "from os import path\n"
        "from os import name\n"
    )
    stream = io.StringIO(attr_code)
    imports_attr = list(find_imports_in_stream(stream, unique=ImportKey.ATTRIBUTE))
    assert len(imports_attr) == 2

    # Test unique=ImportKey.MODULE (covered by lines 569-570)
    mod_code = (
        "import os.path\n"
        "import os.path\n"
        "import os.environ\n"
    )
    stream = io.StringIO(mod_code)
    imports_mod = list(find_imports_in_stream(stream, unique=ImportKey.MODULE))
    assert len(imports_mod) == 2

    # Test unique=ImportKey.PACKAGE (covered by lines 571-572)
    pkg_code = (
        "import os.path\n"
        "import os.environ\n"
        "import sys\n"
    )
    stream = io.StringIO(pkg_code)
    imports_pkg = list(find_imports_in_stream(stream, unique=ImportKey.PACKAGE))
    assert len(imports_pkg) == 2

    # Test with existing _seen and config_kwargs
    stream = io.StringIO("import os\nimport sys\n")
    imports_seen = list(find_imports_in_stream(stream, unique=True, _seen={"import os"}, line_length=80))
    assert len(imports_seen) == 1
    assert imports_seen[0].module == "sys"
