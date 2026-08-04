# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

import pytest
from isort.deprecated.finders import ReqsBaseFinder
from isort.settings import Config

class MockReqsBaseFinder(ReqsBaseFinder):
    enabled = True  # Enable the finder for testing
    names = ['numpy', 'pandas', 'requests']  # Mocked names for testing

    def _get_names(self, path: str):
        return iter(self.names)

    def _get_files_from_dir(self, path: str):
        return iter([])  # No files to return for this mock

    def _load_names(self):
        return self.names

@pytest.fixture
def finder():
    return MockReqsBaseFinder(Config())

def test_find_enabled_with_valid_name(finder):
    result = finder.find('numpy')
    assert result == 'THIRDPARTY'

def test_find_enabled_with_another_valid_name(finder):
    result = finder.find('pandas')
    assert result == 'THIRDPARTY'

def test_find_enabled_with_nonexistent_name(finder):
    result = finder.find('nonexistent')
    assert result is None

def test_find_enabled_with_empty_name(finder):
    result = finder.find('')
    assert result is None

def test_find_disabled(finder):
    finder.enabled = False  # Disable the finder
    result = finder.find('numpy')
    assert result is None
