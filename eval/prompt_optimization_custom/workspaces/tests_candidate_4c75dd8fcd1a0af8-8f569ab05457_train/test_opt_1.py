# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 80, 86, 87, 88, 89, 90, 92, 93, 94, 97, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 80], [80, 86], [86, 87], [86, 97], [88, 89], [90, 92], [92, 93], [97, 100]]}

import pytest
from isort.settings import Config
from isort.sorting import section_key

@pytest.fixture
def config():
    return Config()

def test_section_key_reverse_relative():
    config = Config(sort_relative_in_force_sorted_sections=False, reverse_relative=True)
    line = "from .module import something"
    result = section_key(line, config)
    assert result.startswith("B")  # Should be section B

def test_section_key_group_by_package():
    config = Config(group_by_package=True)
    line = "from package import something"
    result = section_key(line, config)
    assert result == "Bpackage"  # Should return section B with package name

def test_section_key_lexicographical():
    config = Config(lexicographical=True)
    line = "from package import something"
    result = section_key(line, config)
    assert result == "Bpackage.something"  # Should return section B with package name and import

def test_section_key_case_sensitive():
    config = Config(honor_case_in_force_sorted_sections=True, case_sensitive=True, order_by_type=False)
    line = "from Package import something"
    result = section_key(line, config)
    assert result == "BPackage import something"  # Should return original case


def test_section_key_length_sort():
    config = Config(length_sort=True)
    line = "import module"
    result = section_key(line, config)
    assert result == "B6module"  # Should return section B with length of line
