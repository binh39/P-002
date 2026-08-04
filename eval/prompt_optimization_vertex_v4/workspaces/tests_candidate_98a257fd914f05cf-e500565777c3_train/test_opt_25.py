# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

from isort import sections
from isort.deprecated.finders import ReqsBaseFinder
from isort.settings import Config


class DummyReqsFinder(ReqsBaseFinder):
    enabled = True

    def _load_names(self):
        return ["requests", "click"]

    def _get_names(self, path):
        return iter([])

    def _get_files_from_dir(self, path):
        return iter([])


class DisabledDummyReqsFinder(ReqsBaseFinder):
    enabled = False

    def _load_names(self):
        return []

    def _get_names(self, path):
        return iter([])

    def _get_files_from_dir(self, path):
        return iter([])


def test_reqs_base_finder_not_enabled():
    finder = DisabledDummyReqsFinder(Config())
    assert finder.find("requests") is None


def test_reqs_base_finder_empty_module_name():
    finder = DummyReqsFinder(Config())
    assert finder.find("") is None
    assert finder.find(".") is None


def test_reqs_base_finder_match_and_no_match():
    finder = DummyReqsFinder(Config())
    # Exact match after lowercasing and partition
    assert finder.find("Requests.compat") == sections.THIRDPARTY
    assert finder.find("click") == sections.THIRDPARTY
    # No match
    assert finder.find("os") is None
