# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

from unittest.mock import MagicMock
from isort import sections
from isort.deprecated.finders import ReqsBaseFinder


class DummyReqsFinder(ReqsBaseFinder):
    enabled = True
    def _get_names(self, path: str):
        return iter([])
    def _get_files_from_dir(self, path: str):
        return iter([])


def test_reqs_base_finder_not_enabled():
    config = MagicMock()
    finder = DummyReqsFinder(config)
    finder.enabled = False
    assert finder.find("requests") is None


def test_reqs_base_finder_empty_module_name():
    config = MagicMock()
    finder = DummyReqsFinder(config)
    finder.enabled = True
    finder.names = ["requests"]
    
    assert finder.find("") is None
    assert finder.find(".") is None


def test_reqs_base_finder_match_and_no_match():
    config = MagicMock()
    finder = DummyReqsFinder(config)
    finder.enabled = True
    finder.names = ["requests", "django"]

    # Match exact
    assert finder.find("requests") == sections.THIRDPARTY
    # Match with submodules and partitioning (e.g. requests.exceptions)
    assert finder.find("Requests.Exceptions") == sections.THIRDPARTY
    # No match
    assert finder.find("flask") is None
