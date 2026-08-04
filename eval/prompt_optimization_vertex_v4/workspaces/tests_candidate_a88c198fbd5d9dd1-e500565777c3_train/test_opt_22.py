# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

from isort import sections
from isort.deprecated.finders import ReqsBaseFinder
from isort.settings import Config


class DummyReqsFinder(ReqsBaseFinder):
    enabled = True

    def _get_names(self, path: str):
        return iter([])

    def _get_files_from_dir(self, path: str):
        return iter([])


def test_reqs_base_finder_not_enabled():
    finder = DummyReqsFinder(Config(), path=".")
    finder.enabled = False
    assert finder.find("requests") is None


def test_reqs_base_finder_empty_module_name():
    finder = DummyReqsFinder(Config(), path=".")
    finder.enabled = True
    assert finder.find("") is None
    assert finder.find(".") is None


def test_reqs_base_finder_match_and_no_match():
    finder = DummyReqsFinder(Config(), path=".")
    finder.enabled = True
    finder.names = {"requests", "django"}

    # Exact match on module name (case-insensitive)
    assert finder.find("Requests.auth") == sections.THIRDPARTY

    # No match
    assert finder.find("numpy.array") is None
