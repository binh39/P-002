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

    # 1. Test when not enabled (covers line 276 -> returns None)
    finder.enabled = False
    assert finder.find("some_module") is None

    # Re-enable for subsequent checks
    finder.enabled = True
    finder.names = ["requests", "click"]

    # 2. Test when module_name partition results in empty module_name (covers line 281 -> returns None)
    assert finder.find("") is None
    assert finder.find(".") is None

    # 3. Test when module_name matches one in self.names (covers lines 284-286 -> returns THIRDPARTY)
    assert finder.find("requests") == sections.THIRDPARTY
    assert finder.find("Requests.compat") == sections.THIRDPARTY

    # 4. Test when module_name does not match any in self.names (covers line 287 -> returns None)
    assert finder.find("flask") is None
