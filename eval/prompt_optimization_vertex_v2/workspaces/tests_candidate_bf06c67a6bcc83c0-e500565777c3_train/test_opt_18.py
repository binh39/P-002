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
        yield from []

    def _get_files_from_dir(self, path: str):
        yield from []


def test_reqs_base_finder_find():
    config = Config()
    finder = DummyReqsFinder(config)
    finder.enabled = True
    finder.names = ["requests", "click"]

    # 1. Test when enabled is False (covers line 276-277)
    finder.enabled = False
    assert finder.find("requests") is None

    # 2. Test when enabled is True, but module_name is empty after partition (covers line 281-282)
    finder.enabled = True
    assert finder.find("") is None
    assert finder.find(".") is None

    # 3. Test when module_name matches one in self.names (covers lines 284-286)
    assert finder.find("Requests.compat") == sections.THIRDPARTY
    assert finder.find("click") == sections.THIRDPARTY

    # 4. Test when module_name does not match any in self.names (covers lines 284-287)
    assert finder.find("os") is None
