# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

import pytest
from isort import sections
from isort.deprecated.finders import ReqsBaseFinder
from isort.settings import Config

class MockReqsBaseFinder(ReqsBaseFinder):
    def _get_files_from_dir(self, path: str):
        return []

    def _get_names(self, path: str):
        return iter(self.names)

class TestReqsBaseFinder:

    @pytest.fixture
    def finder(self):
        config = Config()
        finder = MockReqsBaseFinder(config=config)
        finder.enabled = True
        finder.names = ['example', 'testmodule']
        return finder

    def test_find_enabled_with_matching_name(self, finder):
        result = finder.find('example')
        assert result == sections.THIRDPARTY

    def test_find_enabled_with_non_matching_name(self, finder):
        result = finder.find('nonexistentmodule')
        assert result is None

    def test_find_enabled_with_empty_name(self, finder):
        result = finder.find('')
        assert result is None

    def test_find_disabled(self, finder):
        finder.enabled = False
        result = finder.find('example')
        assert result is None

    def test_find_with_submodules(self, finder):
        result = finder.find('example.submodule')
        assert result == sections.THIRDPARTY
