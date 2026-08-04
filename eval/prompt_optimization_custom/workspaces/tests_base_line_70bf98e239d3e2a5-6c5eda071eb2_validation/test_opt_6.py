# file: src\sample_repo\isort\isort\wrap.py:10-68
# asked: {"lines": [10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 21, 22, 23, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 42, 43, 44, 45, 46, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 65, 66, 67, 68], "branches": [[20, 21], [20, 25], [42, 43], [42, 66], [45, 46], [45, 48], [50, 51], [50, 66], [66, 67], [66, 68]]}
# gained: {"lines": [10, 13, 14, 16, 17, 20, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 42, 66, 67, 68], "branches": [[20, 25], [42, 66], [66, 67], [66, 68]]}

import pytest
from isort.settings import Config
from isort.wrap_modes import WrapModes as Modes
from isort.wrap import import_statement

@pytest.fixture
def default_config():
    return Config()


def test_import_statement_balanced_wrapping(default_config):
    import_start = "from module import"
    from_imports = ["ClassA", "ClassB", "ClassC", "ClassD"]
    comments = []
    line_separator = "\n"
    config = default_config
    multi_line_output = Modes.VERTICAL
    explode = False

    result = import_statement(import_start, from_imports, comments, line_separator, config, multi_line_output, explode)
    
    assert result.count(line_separator) > 1  # Ensure it wraps to multiple lines



def test_import_statement_without_comments(default_config):
    import_start = "from module import"
    from_imports = ["ClassA", "ClassB"]
    comments = []
    line_separator = "\n"
    config = default_config
    multi_line_output = None
    explode = False

    result = import_statement(import_start, from_imports, comments, line_separator, config, multi_line_output, explode)
    
    assert "This is a comment" not in result  # Ensure comments are not included
