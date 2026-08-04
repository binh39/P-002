# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

from isort.settings import Config
from isort import sections
from isort.deprecated.finders import ReqsBaseFinder


class DummyDisabledReqsFinder(ReqsBaseFinder):
    enabled = False
    def _get_names(self, path: str):
        yield from []
    def _get_files_from_dir(self, path: str):
        yield from []


class DummyReqsFinder(ReqsBaseFinder):
    enabled = True
    def _get_names(self, path: str):
        yield from []
    def _get_files_from_dir(self, path: str):
        yield from []
    def _load_names(self):
        return ["requests", "pytest"]


def test_reqs_base_finder_find():
    config = Config()
    
    # Test when not enabled
    finder_disabled = DummyDisabledReqsFinder(config)
    assert finder_disabled.enabled is False
    assert finder_disabled.find("requests") is None

    # Test when enabled
    finder = DummyReqsFinder(config)

    # 1. Empty module name or partition leading to empty module_name
    assert finder.find("") is None
    assert finder.find(".") is None

    # 2. Matching module_name
    assert finder.find("Requests") == sections.THIRDPARTY
    assert finder.find("pytest.mark") == sections.THIRDPARTY

    # 3. Non-matching module_name
    assert finder.find("flask") is None
