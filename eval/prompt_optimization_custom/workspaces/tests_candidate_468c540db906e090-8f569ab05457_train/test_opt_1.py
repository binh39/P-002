# file: src\sample_repo\isort\isort\wrap_modes.py:117-167
# asked: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}
# gained: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 135, 136, 146, 147, 148, 149, 150, 151, 153, 154, 156, 167], "branches": [[119, 120], [119, 122], [127, 135], [136, 146], [146, 147], [146, 167], [153, 156]]}

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
    """Test hanging_indent with no imports."""
    result = hanging_indent(**interface)
    assert result == ""


def test_hanging_indent_exceeds_line_length(interface):
    """Test hanging_indent when the import exceeds line length."""
    interface["imports"] = ["long_module_name"]
    interface["statement"] = "import "
    result = hanging_indent(**interface)
    assert result == "import long_module_name"



def test_hanging_indent_with_long_imports_and_comments(interface):
    """Test hanging_indent with long imports and comments."""
    interface["imports"] = ["long_module_name"]
    interface["statement"] = "import "
    interface["comments"] = ["This is a long import"]
    result = hanging_indent(**interface)
    expected = isort.comments.add_to_line(interface["comments"], "import long_module_name", removed=False, comment_prefix=interface["comment_prefix"])
    assert result == expected
