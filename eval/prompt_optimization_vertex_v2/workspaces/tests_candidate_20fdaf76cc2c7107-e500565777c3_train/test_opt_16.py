# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

from isort import sections
from isort.deprecated.finders import ReqsBaseFinder
from isort.settings import Config


class DummyReqsFinder(ReqsBaseFinder):
    def _get_names(self, path: str):
        return iter([])

    def _get_files_from_dir(self, path: str):
        return iter([])


def test_reqs_base_finder_not_enabled():
    config = Config()
    finder = DummyReqsFinder(config)
    finder.enabled = False

    result = finder.find("some_module")
    assert result is None


def test_reqs_base_finder_empty_module_name():
    config = Config()
    finder = DummyReqsFinder(config)
    finder.enabled = True
    finder.names = ["requests"]

    result = finder.find("")
    assert result is None


def test_reqs_base_finder_matches_name():
    config = Config()
    finder = DummyReqsFinder(config)
    finder.enabled = True
    finder.names = ["requests", "click"]

    # Tests matching name and partition behavior (submodules stripped)
    result = finder.find("Requests.compat")
    assert result == sections.THIRDPARTY


def test_reqs_base_finder_no_match():
    config = Config()
    finder = DummyReqsFinder(config)
    finder.enabled = True
    finder.names = ["requests", "click"]

    result = finder.find("flask.app")
    assert result is None
