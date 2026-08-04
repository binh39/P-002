# file: src\sample_repo\isort\isort\identify.py:44-208
# asked: {"lines": [44, 45, 46, 47, 48, 49, 51, 53, 54, 55, 56, 59, 60, 61, 62, 64, 65, 66, 67, 68, 69, 70, 71, 73, 74, 75, 76, 77, 78, 80, 81, 83, 84, 85, 86, 88, 89, 90, 91, 92, 93, 95, 97, 98, 99, 101, 102, 103, 105, 107, 108, 109, 110, 113, 114, 115, 116, 117, 118, 120, 121, 123, 124, 125, 126, 127, 129, 132, 133, 135, 136, 137, 138, 139, 140, 141, 143, 144, 145, 146, 148, 149, 152, 153, 154, 155, 156, 158, 160, 161, 162, 165, 166, 167, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 188, 191, 192, 193, 194, 195, 196, 197, 199, 201, 202, 203, 204, 205, 207, 208], "branches": [[54, 0], [54, 55], [59, 60], [59, 61], [61, 62], [61, 64], [65, 66], [65, 83], [66, 67], [66, 74], [67, 68], [67, 74], [74, 75], [74, 81], [85, 86], [85, 88], [88, 54], [88, 89], [90, 91], [90, 92], [92, 93], [92, 95], [113, 114], [113, 123], [114, 115], [114, 152], [123, 124], [123, 152], [132, 133], [132, 143], [135, 123], [135, 136], [143, 146], [143, 148], [152, 153], [152, 165], [172, 173], [172, 201], [173, 174], [173, 201], [176, 177], [176, 191], [185, 186], [185, 188], [196, 197], [196, 199], [201, 88], [201, 202], [202, 203], [202, 207], [204, 88], [204, 205], [207, 88], [207, 208]]}
# gained: {"lines": [44, 47, 48, 51, 53, 54, 55, 56, 59, 60, 61, 64, 65, 66, 74, 75, 76, 80, 81, 83, 84, 85, 86, 88, 89, 90, 91, 92, 93, 97, 98, 99, 101, 102, 103, 105, 107, 108, 109, 110, 113, 114, 115, 116, 120, 121, 123, 124, 125, 129, 132, 143, 144, 145, 148, 149, 152, 153, 154, 155, 156, 158, 160, 161, 162, 165, 166, 167, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 188, 191, 192, 193, 194, 195, 196, 197, 201, 202, 203, 204, 205, 207, 208], "branches": [[54, 0], [54, 55], [59, 60], [59, 61], [61, 64], [65, 66], [65, 83], [66, 74], [74, 75], [74, 81], [85, 86], [85, 88], [88, 54], [88, 89], [90, 91], [90, 92], [92, 93], [113, 114], [113, 123], [114, 115], [114, 152], [123, 124], [123, 152], [132, 143], [143, 148], [152, 153], [152, 165], [172, 173], [172, 201], [173, 174], [173, 201], [176, 177], [176, 191], [185, 186], [185, 188], [196, 197], [201, 88], [201, 202], [202, 203], [202, 207], [204, 88], [204, 205], [207, 88], [207, 208]]}

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
    content2 = "def foo():\n    import os\n"
    stream2 = io.StringIO(content2, newline="\n")
    res = list(imports(stream2, top_only=True))
    assert len(res) == 0


def test_imports_raise_yield_and_continuation():
    # Lines 65-81 skip raise/yield statements and any backslash continuation lines following them.
    # So "raise ValueError \n import os" will skip the raise and its continuation line, but import os comes after.
    content = (
        "raise ValueError \\\n"
        "    and_some_continuation\n"
        "yield \\\n"
        "    more_continuation\n"
        "import os\n"
    )
    stream = io.StringIO(content, newline="\n")
    res = list(imports(stream))
    assert len(res) == 1
    assert res[0].module == "os"


def test_imports_semicolon_and_comment():
    content = "import os; import sys # comment\n"
    stream = io.StringIO(content, newline="\n")
    res = list(imports(stream))
    assert len(res) == 2
    assert res[0].module == "os"
    assert res[1].module == "sys"


def test_imports_parentheses_multiline():
    content = (
        "from os import (\n"
        "    environ as env,\n"
        "    path,\n"
        ")\n"
    )
    stream = io.StringIO(content, newline="\n")
    res = list(imports(stream))
    assert len(res) == 2
    assert res[0].module == "os"
    assert res[0].attribute == "environ"
    assert res[0].alias == "env"
    assert res[1].module == "os"
    assert res[1].attribute == "path"


def test_imports_escaped_line_with_parentheses():
    content = (
        "from os import \\\n"
        "    (path)\n"
    )
    stream = io.StringIO(content, newline="\n")
    res = list(imports(stream))
    assert len(res) == 1
    assert res[0].module == "os"
    assert res[0].attribute == "path"


def test_imports_escaped_line_without_parentheses_matching_import():
    content = (
        "import \\\n"
        "    os\n"
    )
    stream = io.StringIO(content, newline="\n")
    res = list(imports(stream))
    assert len(res) == 1
    assert res[0].module == "os"


def test_imports_escaped_line_without_parentheses_else_branch():
    content = (
        "import os \\\n"
        "    sys\n"
    )
    stream = io.StringIO(content, newline="\n")
    res = list(imports(stream))
    assert len(res) >= 1


def test_imports_cimport():
    content = "import cimport foo\nfrom foo cimport bar\n"
    stream = io.StringIO(content, newline="\n")
    res = list(imports(stream))
    assert len(res) >= 1


def test_imports_redundant_aliases():
    config = Config(remove_redundant_aliases=True)
    content = "import os as os\nfrom sys import path as path\n"
    stream = io.StringIO(content, newline="\n")
    res = list(imports(stream, config=config))
    assert len(res) == 2
    assert res[0].alias is None
    assert res[1].alias is None
