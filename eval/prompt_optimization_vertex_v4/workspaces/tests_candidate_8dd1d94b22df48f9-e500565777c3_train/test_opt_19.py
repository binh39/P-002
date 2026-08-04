# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

from unittest.mock import MagicMock
from isort import sections
from isort.deprecated.finders import ReqsBaseFinder
from isort.settings import Config


class DummyReqsFinder(ReqsBaseFinder):
    enabled = True

    def _get_names(self, path: str):
        return iter([])

    def _get_files_from_dir(self, path: str):
        return iter([])


def test_reqs_base_finder_find_coverage():
    config = MagicMock(spec=Config)
    
    # Test case 1: enabled = False (lines 276-277)
    finder_disabled = DummyReqsFinder(config)
    finder_disabled.enabled = False
    assert finder_disabled.find("some_module") is None

    # Test case 2: empty module_name after partition/lower (lines 281-282)
    finder_enabled = DummyReqsFinder(config)
    finder_enabled.enabled = True
    finder_enabled.names = ["requests"]
    assert finder_enabled.find("") is None
    assert finder_enabled.find(".") is None

    # Test case 3: module_name matches in self.names (lines 284-286)
    assert finder_enabled.find("Requests.foo") == sections.THIRDPARTY

    # Test case 4: module_name does not match in self.names (lines 284-287)
    assert finder_enabled.find("numpy.array") is None
