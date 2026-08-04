# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

from isort import sections
from isort.deprecated.finders import ReqsBaseFinder
from isort.settings import Config


def test_reqs_base_finder_find():
    config = Config()

    # Create a concrete subclass of ReqsBaseFinder implementing abstract methods
    class DummyReqsFinder(ReqsBaseFinder):
        def _get_names(self, path: str):
            iter([])

        def _get_files_from_dir(self, path: str):
            iter([])

    finder = DummyReqsFinder(config)

    # 1. Test when enabled is False (covers line 276-277)
    finder.enabled = False
    assert finder.find("some_module") is None

    # 2. Test when enabled is True, but module_name is empty after partition/lower (covers lines 281-282)
    finder.enabled = True
    assert finder.find("") is None
    assert finder.find(".") is None

    # 3. Test matching and non-matching names (covers lines 284-287)
    finder.names = ["requests", "flask"]

    # Match exact
    assert finder.find("requests") == sections.THIRDPARTY
    # Match case-insensitive and with submodules/separator
    assert finder.find("REQUESTS.models") == sections.THIRDPARTY
    # No match
    assert finder.find("django") is None
