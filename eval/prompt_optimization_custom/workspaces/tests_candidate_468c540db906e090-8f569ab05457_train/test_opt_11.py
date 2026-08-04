# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

import pytest
from isort.deprecated.finders import ReqsBaseFinder
from isort import sections
from isort.settings import Config
from collections.abc import Iterator

class MockReqsBaseFinder(ReqsBaseFinder):
    def __init__(self):
        super().__init__(Config())
        self.enabled = True
        self.names = ['example', 'testmodule']

    def _get_names(self, path: str) -> Iterator[str]:
        return iter(self.names)

    def _get_files_from_dir(self, path: str) -> Iterator[str]:
        return iter([])

@pytest.fixture
def finder():
    """Fixture to create a MockReqsBaseFinder instance for testing."""
    return MockReqsBaseFinder()

def test_find_module_not_enabled(finder):
    """Test the find method when the finder is not enabled."""
    finder.enabled = False
    result = finder.find('example')
    assert result is None

def test_find_empty_module_name(finder):
    """Test the find method with an empty module name."""
    result = finder.find('')
    assert result is None

def test_find_module_not_in_names(finder):
    """Test the find method when the module name is not in names."""
    result = finder.find('nonexistentmodule')
    assert result is None

def test_find_module_in_names(finder):
    """Test the find method when the module name is in names."""
    result = finder.find('example')
    assert result == sections.THIRDPARTY

def test_find_module_with_submodules(finder):
    """Test the find method with a module name that has submodules."""
    result = finder.find('example.submodule')
    assert result == sections.THIRDPARTY
