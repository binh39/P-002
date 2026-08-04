# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

import pytest
from isort.deprecated.finders import ReqsBaseFinder
from isort.settings import Config
from isort import sections


class DummyReqsFinder(ReqsBaseFinder):
    enabled = True
    def _get_names(self, path: str):
        return iter([])
    def _get_files_from_dir(self, path: str):
        return iter([])


def test_reqs_base_finder_find():
    config = Config()
    finder = DummyReqsFinder(config)
    finder.enabled = False
    finder.names = ["requests"]

    # Test when not enabled (line 276 -> returns None)
    assert finder.find("requests") is None

    # Re-enable
    finder.enabled = True

    # Test when module_name is empty after partition or empty string (line 281 -> returns None)
    assert finder.find("") is None
    assert finder.find(".") is None

    # Test matching name in self.names (lines 284-286 -> returns THIRDPARTY)
    finder.names = ["requests", "click"]
    assert finder.find("requests") == sections.THIRDPARTY
    assert finder.find("Requests.submodule") == sections.THIRDPARTY

    # Test non-matching name (line 287 -> returns None)
    assert finder.find("flask") is None
