# file: src\sample_repo\isort\isort\wrap_modes.py:117-167
# asked: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}
# gained: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 167], "branches": [[119, 120], [119, 122], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156]]}

import pytest
import isort.comments
from isort.wrap_modes import hanging_indent

@pytest.fixture
def interface():
    return {
        "imports": [],
        "line_length": 80,
        "statement": "",
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "# ",
    }

def test_hanging_indent_no_imports(interface):
    interface["imports"] = []
    result = hanging_indent(**interface)
    assert result == ""

def test_hanging_indent_single_import(interface):
    interface["imports"] = ["import os"]
    result = hanging_indent(**interface)
    assert result == "import os"

def test_hanging_indent_exceeds_line_length(interface):
    interface["imports"] = ["import long_module_name_1", "import long_module_name_2"]
    interface["line_length"] = 30  # Set a low line length to trigger hanging indent
    result = hanging_indent(**interface)
    assert result.startswith("import long_module_name_1")
    assert "import long_module_name_2" in result

def test_hanging_indent_with_comments(interface):
    interface["imports"] = ["import os"]
    interface["comments"] = ["This is a comment"]
    result = hanging_indent(**interface)
    assert result == isort.comments.add_to_line(interface["comments"], "import os", removed=False, comment_prefix=interface["comment_prefix"])

def test_hanging_indent_with_multiple_imports(interface):
    interface["imports"] = ["import os", "import sys", "import json"]
    interface["line_length"] = 50  # Set a line length that allows multiple imports
    result = hanging_indent(**interface)
    assert "import os, import sys, import json" in result

def test_hanging_indent_with_long_imports(interface):
    interface["imports"] = ["import long_module_name_1", "import long_module_name_2"]
    interface["line_length"] = 40  # Set a line length that will require hanging indent
    result = hanging_indent(**interface)
    assert "import long_module_name_1" in result
    assert "import long_module_name_2" in result
    assert result.startswith("import long_module_name_1")
    assert result.count("\n") > 0  # Ensure that there is a hanging indent
