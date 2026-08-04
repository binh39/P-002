# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

from isort.deprecated.finders import ReqsBaseFinder
from isort.sections import THIRDPARTY
from isort.settings import Config


class DummyReqsFinder(ReqsBaseFinder):
    enabled = True

    def _get_names(self, path: str):
        return iter([])

    def _get_files_from_dir(self, path: str):
        return iter([])


def test_reqs_base_finder_find():
    config = Config()
    finder = DummyReqsFinder(config)
    finder.names = ["requests", "pytest"]

    # 1. Test when not enabled
    finder.enabled = False
    assert finder.find("requests") is None

    # Re-enable for subsequent checks
    finder.enabled = True

    # 2. Test when module_name is empty or just dots resulting in empty lower name
    assert finder.find("") is None
    assert finder.find(".") is None

    # 3. Test when module_name matches one in self.names (with submodules, casing, etc.)
    assert finder.find("Requests") == THIRDPARTY
    assert finder.find("pytest.submodule") == THIRDPARTY

    # 4. Test when module_name does not match any name in self.names
    assert finder.find("flask") is None
