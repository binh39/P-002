# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

from isort.settings import Config
from isort.deprecated.finders import ReqsBaseFinder
from isort import sections


class ConcreteReqsFinder(ReqsBaseFinder):
    enabled = True
    
    def _get_names(self, path: str):
        yield from []

    def _get_files_from_dir(self, path: str):
        yield from []


def test_reqs_base_finder_find_paths():
    config = Config()
    
    # 1. Test when enabled is False (line 276-277)
    ReqsBaseFinder.enabled = False
    finder_disabled = ConcreteReqsFinder(config)
    assert finder_disabled.find("some_module") is None

    # Enable for subsequent tests
    ReqsBaseFinder.enabled = True
    finder = ConcreteReqsFinder(config)
    
    # Reset/set self.names explicitly to test the loop and conditions
    finder.names = {"requests", "django"}

    # 2. Test when module_name is empty after partition (line 281-282)
    assert finder.find("") is None
    assert finder.find(".") is None

    # 3. Test when module_name matches one of self.names (line 284-286)
    assert finder.find("Requests") == sections.THIRDPARTY
    assert finder.find("django.http") == sections.THIRDPARTY

    # 4. Test when module_name does not match any of self.names (line 284-287)
    assert finder.find("unknown_module") is None

    # Cleanup state
    ReqsBaseFinder.enabled = False
