# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

import pytest
from isort import sections
from isort.deprecated.finders import ReqsBaseFinder
from isort.settings import Config


class DummyReqsFinder(ReqsBaseFinder):
    enabled = True
    def _get_names(self, path: str):
        return iter([])
    def _get_files_from_dir(self, path: str):
        return iter([])


def test_reqs_base_finder_find():
    config = Config()
    
    # 1. Test when enabled is False (covers line 276-277)
    class DisabledFinder(ReqsBaseFinder):
        enabled = False
        def _get_names(self, path: str):
            return iter([])
        def _get_files_from_dir(self, path: str):
            return iter([])

    disabled_finder = DisabledFinder(config)
    assert disabled_finder.find("some_module") is None

    # 2. Test when enabled is True, but module_name is empty or just dots/separators (covers line 281-282)
    finder = DummyReqsFinder(config)
    finder.names = ["requests"]
    
    assert finder.find("") is None
    assert finder.find(".") is None

    # 3. Test when module_name matches one of self.names (covers lines 284-286)
    assert finder.find("Requests") == sections.THIRDPARTY
    assert finder.find("requests.compat") == sections.THIRDPARTY

    # 4. Test when module_name does not match self.names (covers line 287)
    assert finder.find("urllib3") is None
