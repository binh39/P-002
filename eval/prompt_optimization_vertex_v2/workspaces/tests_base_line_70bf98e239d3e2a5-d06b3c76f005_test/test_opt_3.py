# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

from isort.deprecated.finders import ReqsBaseFinder
from isort.settings import Config
from isort import sections


class DummyReqsFinder(ReqsBaseFinder):
    enabled = True
    def _get_names(self, path: str):
        yield from []
    def _get_files_from_dir(self, path: str):
        yield from []


def test_reqs_base_finder_find():
    config = Config()
    finder = DummyReqsFinder(config)
    finder.enabled = False
    
    # test disabled finder -> returns None
    assert finder.find("requests") is None

    # re-enable
    finder.enabled = True
    finder.names = ["requests", "foo"]

    # test empty module name or partition leading to empty
    assert finder.find("") is None
    assert finder.find(".") is None

    # test matching name -> THIRDPARTY
    assert finder.find("Requests.sub") == sections.THIRDPARTY
    assert finder.find("foo") == sections.THIRDPARTY

    # test non-matching name -> None
    assert finder.find("bar") is None
