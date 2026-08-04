# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

from isort.settings import Config
from isort.deprecated.finders import ReqsBaseFinder
from isort import sections


class DummyReqsFinder(ReqsBaseFinder):
    enabled = True
    def _get_names(self, path: str):
        return iter([])
    def _get_files_from_dir(self, path: str):
        return iter([])


def test_reqs_base_finder_find():
    config = Config()
    finder = DummyReqsFinder(config)
    finder.enabled = True
    finder.names = {"requests", "pytest"}

    # 1. Test when enabled is False
    finder.enabled = False
    assert finder.find("requests") is None

    # 2. Test when enabled is True, but module_name is empty after partition/lower
    finder.enabled = True
    assert finder.find("") is None
    assert finder.find(".") is None

    # 3. Test when module_name matches one of the names (returns THIRDPARTY)
    assert finder.find("Requests") == sections.THIRDPARTY
    assert finder.find("pytest.submodule") == sections.THIRDPARTY

    # 4. Test when module_name does not match any name (returns None)
    assert finder.find("unknown_module") is None
