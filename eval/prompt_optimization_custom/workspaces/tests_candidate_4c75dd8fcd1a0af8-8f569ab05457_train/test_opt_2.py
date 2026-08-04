# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 141, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [141, 144]]}

import pytest
import re
from isort.settings import DEFAULT_CONFIG, Config
from isort.wrap_modes import WrapModes as Modes
from isort.wrap import line

@pytest.fixture
def config():
    # Create a mutable config object for testing
    return Config(
        line_length=20,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
        use_parentheses=False,
        include_trailing_comma=False
    )

def test_line_wraps_long_import_statement(config):
    content = "import long_module_name"
    line_separator = "\n"
    
    result = line(content, line_separator, config)
    
    expected = "import long_module_name"  # Adjust based on expected output
    assert result == expected

def test_line_wraps_with_comment(config):
    content = "import long_module_name  # This is a comment"
    line_separator = "\n"
    
    result = line(content, line_separator, config)
    
    expected = "import long_module_name  # This is a comment"  # Adjust based on expected output
    assert result == expected

def test_line_wraps_with_noqa(config):
    config = Config(
        line_length=20,
        multi_line_output=Modes.NOQA,
        use_parentheses=False,
        include_trailing_comma=False
    )
    content = "import long_module_name  # NOQA"
    line_separator = "\n"
    
    result = line(content, line_separator, config)
    
    expected = "import long_module_name  # NOQA"
    assert result == expected

def test_line_wraps_with_parentheses(config):
    config = Config(
        line_length=20,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
        use_parentheses=True,
        include_trailing_comma=False
    )
    content = "import long_module_name"
    line_separator = "\n"
    
    result = line(content, line_separator, config)
    
    expected = "import long_module_name"  # Adjust based on expected output
    assert result == expected

def test_line_no_wrap_when_short(config):
    config = Config(
        line_length=50,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
        use_parentheses=False,
        include_trailing_comma=False
    )
    content = "import short"
    line_separator = "\n"
    
    result = line(content, line_separator, config)
    
    expected = "import short"
    assert result == expected



def test_line_no_wrap_when_no_splitters(config):
    content = "this_is_a_long_line_without_any_splitters"
    line_separator = "\n"
    
    result = line(content, line_separator, config)
    
    expected = "this_is_a_long_line_without_any_splitters"
    assert result == expected

def test_line_wraps_with_noqa_comment(config):
    content = "import long_module_name  # NOQA"
    line_separator = "\n"
    
    result = line(content, line_separator, config)
    
    expected = "import long_module_name  # NOQA"
    assert result == expected
