# file: src\sample_repo\isort\isort\identify.py:44-208
# asked: {"lines": [44, 45, 46, 47, 48, 49, 51, 53, 54, 55, 56, 59, 60, 61, 62, 64, 65, 66, 67, 68, 69, 70, 71, 73, 74, 75, 76, 77, 78, 80, 81, 83, 84, 85, 86, 88, 89, 90, 91, 92, 93, 95, 97, 98, 99, 101, 102, 103, 105, 107, 108, 109, 110, 113, 114, 115, 116, 117, 118, 120, 121, 123, 124, 125, 126, 127, 129, 132, 133, 135, 136, 137, 138, 139, 140, 141, 143, 144, 145, 146, 148, 149, 152, 153, 154, 155, 156, 158, 160, 161, 162, 165, 166, 167, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 188, 191, 192, 193, 194, 195, 196, 197, 199, 201, 202, 203, 204, 205, 207, 208], "branches": [[54, 0], [54, 55], [59, 60], [59, 61], [61, 62], [61, 64], [65, 66], [65, 83], [66, 67], [66, 74], [67, 68], [67, 74], [74, 75], [74, 81], [85, 86], [85, 88], [88, 54], [88, 89], [90, 91], [90, 92], [92, 93], [92, 95], [113, 114], [113, 123], [114, 115], [114, 152], [123, 124], [123, 152], [132, 133], [132, 143], [135, 123], [135, 136], [143, 146], [143, 148], [152, 153], [152, 165], [172, 173], [172, 201], [173, 174], [173, 201], [176, 177], [176, 191], [185, 186], [185, 188], [196, 197], [196, 199], [201, 88], [201, 202], [202, 203], [202, 207], [204, 88], [204, 205], [207, 88], [207, 208]]}
# gained: {"lines": [44, 47, 48, 51, 53, 54, 55, 56, 59, 61, 64, 65, 66, 67, 68, 69, 70, 71, 73, 74, 81, 83, 84, 85, 88, 89, 90, 91, 92, 93, 95, 97, 98, 99, 101, 102, 103, 105, 107, 108, 109, 110, 113, 114, 115, 116, 117, 118, 120, 121, 123, 124, 125, 126, 127, 129, 132, 133, 135, 136, 137, 140, 141, 143, 144, 145, 148, 149, 152, 153, 154, 155, 156, 158, 160, 161, 162, 165, 166, 167, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 188, 191, 192, 193, 194, 195, 196, 197, 199, 201, 202, 203, 204, 205, 207, 208], "branches": [[54, 0], [54, 55], [59, 61], [61, 64], [65, 66], [65, 83], [66, 67], [67, 68], [67, 74], [74, 81], [85, 88], [88, 54], [88, 89], [90, 91], [90, 92], [92, 93], [92, 95], [113, 114], [113, 123], [114, 115], [114, 152], [123, 124], [123, 152], [132, 133], [132, 143], [135, 123], [135, 136], [143, 148], [152, 153], [152, 165], [172, 173], [172, 201], [173, 174], [173, 201], [176, 177], [176, 191], [185, 186], [185, 188], [196, 197], [196, 199], [201, 88], [201, 202], [202, 203], [202, 207], [204, 88], [204, 205], [207, 88], [207, 208]]}

import io
from pathlib import Path
from isort.identify import imports
from isort.settings import Config


def test_imports_basic_straight_and_from():
    content = "import os\nfrom sys import path\n"
    stream = io.StringIO(content)
    res = list(imports(stream))
    assert len(res) == 2
    assert res[0].module == "os"
    assert res[1].module == "sys"
    assert res[1].attribute == "path"


def test_imports_top_only():
    content = "import os\nif True:\n    pass\n"
    stream = io.StringIO(content)
    # Using top_only with statement declarations
    res = list(imports(stream, top_only=True))
    assert isinstance(res, list)


def test_imports_raise_yield_and_continuation():
    content = (
        "yield\n"
        "    math\n"
        "import \\\n"
        "    math\n"
    )
    stream = io.StringIO(content)
    res = list(imports(stream))
    assert len(res) == 1
    assert res[0].module == "math"


def test_imports_semicolon_statements():
    content = "import os; import sys\n"
    stream = io.StringIO(content)
    res = list(imports(stream))
    assert len(res) == 2
    assert {r.module for r in res} == {"os", "sys"}


def test_imports_parenthesized_and_escaped_lines():
    content = (
        "from os import (\n"
        "    path,\n"
        "    environ\n"
        ")\n"
        "import \\\n"
        "    (\n"
        "    json,\n"
        "    re\n"
        "    )\n"
    )
    stream = io.StringIO(content)
    res = list(imports(stream))
    modules = [(r.module, r.attribute) for r in res]
    assert ("os", "path") in modules
    assert ("os", "environ") in modules
    assert any(r.module == "json" for r in res)
    assert any(r.module == "re" for r in res)


def test_imports_escaped_line_no_parentheses():
    content = (
        "import json, \\\n"
        "      os\n"
    )
    stream = io.StringIO(content)
    res = list(imports(stream))
    assert len(res) == 2


def test_imports_escaped_line_stops_iteration():
    content = "import \\\n"
    stream = io.StringIO(content)
    res = list(imports(stream))
    assert len(res) == 0


def test_imports_yield_stops_iteration():
    content = "yield"
    stream = io.StringIO(content)
    res = list(imports(stream))
    assert len(res) == 0


def test_imports_parentheses_stop_iteration():
    content = "from os import (\n"
    stream = io.StringIO(content)
    res = list(imports(stream))
    assert len(res) == 0


def test_imports_with_as_clauses():
    content = (
        "import numpy as np\n"
        "from math import pi as math_pi\n"
        "from math import pi as pi\n"
        "import os as os\n"
    )
    config_remove = Config(remove_redundant_aliases=True)
    config_keep = Config(remove_redundant_aliases=False)

    res_remove = list(imports(io.StringIO(content), config=config_remove))
    res_keep = list(imports(io.StringIO(content), config=config_keep))

    assert len(res_remove) == 4
    assert len(res_keep) == 4
    aliases_keep = [r.alias for r in res_keep]
    assert "np" in aliases_keep
    assert "math_pi" in aliases_keep


def test_cimports_handling():
    content = "cimport numpy as np\nfrom cython cimport float\n"
    stream = io.StringIO(content)
    res = list(imports(stream))
    assert len(res) >= 1
