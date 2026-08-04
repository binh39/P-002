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
    
    # Test when not enabled
    assert finder.find("requests") is None

    # Enable and test empty module name
    finder.enabled = True
    finder.names = ["requests"]
    assert finder.find("") is None
    assert finder.find(".") is None

    # Test matching module name
    assert finder.find("Requests.foo") == sections.THIRDPARTY
    assert finder.find("requests") == sections.THIRDPARTY

    # Test non-matching module name
    assert finder.find("urllib") is None
