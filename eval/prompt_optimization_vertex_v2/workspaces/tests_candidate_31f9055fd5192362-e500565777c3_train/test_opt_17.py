# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

import pytest
from isort import sections
from isort.deprecated.finders import ReqsBaseFinder
from isort.settings import Config


class DummyReqsFinder(ReqsBaseFinder):
    # Override abstract methods so we can instantiate it
    def _get_names(self, path: str):
        return iter([])

    def _get_files_from_dir(self, path: str):
        return iter([])


def test_reqs_base_finder_not_enabled():
    config = Config()
    finder = DummyReqsFinder(config)
    # self.enabled is False by default
    assert finder.find("some_module") is None


def test_reqs_base_finder_empty_module_name():
    config = Config()
    finder = DummyReqsFinder(config)
    finder.enabled = True
    finder.names = ["requests"]
    # Empty string or just dots should result in empty module_name after partition
    assert finder.find("") is None
    assert finder.find(".") is None


def test_reqs_base_finder_found():
    config = Config()
    finder = DummyReqsFinder(config)
    finder.enabled = True
    finder.names = ["requests", "click"]
    
    # Matching module name (case-insensitive and submodules check)
    assert finder.find("Requests.compat") == sections.THIRDPARTY
    assert finder.find("click") == sections.THIRDPARTY


def test_reqs_base_finder_not_found():
    config = Config()
    finder = DummyReqsFinder(config)
    finder.enabled = True
    finder.names = ["requests", "click"]
    
    # Non-matching module name
    assert finder.find("flask") is None
