# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

from isort.settings import Config
from isort.deprecated.finders import ReqsBaseFinder
from isort import sections


class DummyReqsFinder(ReqsBaseFinder):
    enabled = True
    def _get_names(self, path: str):
        yield from []
    def _get_files_from_dir(self, path: str):
        yield from []


def test_reqs_base_finder_find_branches():
    config = Config()
    
    # Test when self.enabled is False (lines 276-277)
    finder_disabled = DummyReqsFinder(config)
    finder_disabled.enabled = False
    assert finder_disabled.find("requests") is None

    # Enable finder for subsequent tests
    finder = DummyReqsFinder(config)
    finder.enabled = True
    finder.names = ["requests", "django"]

    # Test when module_name is empty after partition and lower (lines 281-282)
    assert finder.find("") is None
    assert finder.find(".") is None

    # Test when module_name matches self.names (lines 284-286)
    assert finder.find("Requests") == sections.THIRDPARTY
    assert finder.find("django.http") == sections.THIRDPARTY

    # Test when module_name does not match self.names (lines 284, 287)
    assert finder.find("unknown_module") is None
