# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

from unittest.mock import MagicMock
from isort import sections
from isort.deprecated.finders import ReqsBaseFinder
from isort.settings import Config


class ConcreteReqsFinder(ReqsBaseFinder):
    def _get_names(self, path: str):
        iter([])

    def _get_files_from_dir(self, path: str):
        iter([])


def test_reqs_base_finder_find_not_enabled():
    config = MagicMock(spec=Config)
    finder = ConcreteReqsFinder(config)
    finder.enabled = False
    assert finder.find("some_module") is None


def test_reqs_base_finder_find_empty_module_name():
    config = MagicMock(spec=Config)
    finder = ConcreteReqsFinder(config)
    finder.enabled = True
    finder.names = ["requests"]
    assert finder.find("") is None
    assert finder.find(".") is None


def test_reqs_base_finder_find_match_and_no_match():
    config = MagicMock(spec=Config)
    finder = ConcreteReqsFinder(config)
    finder.enabled = True
    finder.names = ["requests", "click"]

    # Match exact name (case-insensitive and with submodules)
    assert finder.find("Requests.compat") == sections.THIRDPARTY
    assert finder.find("click") == sections.THIRDPARTY

    # No match
    assert finder.find("flask.app") is None
