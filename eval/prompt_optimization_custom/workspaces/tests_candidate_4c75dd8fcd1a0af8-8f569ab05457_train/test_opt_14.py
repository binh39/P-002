# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

import pytest
from isort.deprecated.finders import ReqsBaseFinder
from isort import sections
from isort.settings import Config
from collections.abc import Iterator

class MockReqsBaseFinder(ReqsBaseFinder):
    """A mock implementation of ReqsBaseFinder for testing purposes."""
    
    def _get_names(self, path: str) -> Iterator[str]:
        return iter(self.names)

    def _get_files_from_dir(self, path: str) -> Iterator[str]:
        return iter([])  # Mock implementation, returns no files

class TestReqsBaseFinder:
    @pytest.fixture
    def finder(self):
        """Fixture to create a MockReqsBaseFinder instance."""
        finder = MockReqsBaseFinder(config=Config())
        finder.enabled = True  # Ensure the finder is enabled for tests
        finder.names = ['example']  # Add a sample name for testing
        return finder

    def test_find_disabled(self, finder):
        """Test the find method when the finder is disabled."""
        finder.enabled = False
        result = finder.find("example")
        assert result is None  # Should return None when disabled

    def test_find_empty_module_name(self, finder):
        """Test the find method with an empty module name."""
        result = finder.find("")
        assert result is None  # Should return None for empty module name

    def test_find_non_matching_module_name(self, finder):
        """Test the find method with a non-matching module name."""
        result = finder.find("nonexistent")
        assert result is None  # Should return None for non-matching name

    def test_find_matching_module_name(self, finder):
        """Test the find method with a matching module name."""
        result = finder.find("example")
        assert result == sections.THIRDPARTY  # Should return THIRDPARTY for matching name
