# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

import pytest
from isort import sections
from isort.settings import Config
from isort.deprecated.finders import ReqsBaseFinder


class DummyReqsFinder(ReqsBaseFinder):
    enabled = True

    def _get_names(self, path: str):
        return iter([])

    def _get_files_from_dir(self, path: str):
        return iter([])


def test_reqs_base_finder_not_enabled():
    config = Config()
    finder = DummyReqsFinder(config)
    finder.enabled = False
    
    # Hits line 276 (if not self.enabled: return None)
    assert finder.find("requests") is None


def test_reqs_base_finder_empty_module_name():
    config = Config()
    finder = DummyReqsFinder(config)
    finder.enabled = True
    finder.names = {"requests"}

    # Hits line 281 (if not module_name: return None) via partition on "."
    assert finder.find("") is None
    assert finder.find(".submodule") is None


def test_reqs_base_finder_match_found():
    config = Config()
    finder = DummyReqsFinder(config)
    finder.enabled = True
    finder.names = {"requests", "pytest"}

    # Hits line 286 (return sections.THIRDPARTY)
    assert finder.find("Requests.utils") == sections.THIRDPARTY
    assert finder.find("pytest") == sections.THIRDPARTY


def test_reqs_base_finder_no_match():
    config = Config()
    finder = DummyReqsFinder(config)
    finder.enabled = True
    finder.names = {"requests"}

    # Hits line 287 (return None) after loop finishes without matching
    assert finder.find("flask") is None
