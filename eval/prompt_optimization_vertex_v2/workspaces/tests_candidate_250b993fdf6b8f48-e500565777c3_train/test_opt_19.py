# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

from isort.deprecated.finders import ReqsBaseFinder
from isort.settings import Config


class DummyReqsFinder(ReqsBaseFinder):
    enabled = True
    def _get_names(self, path: str):
        yield from []
    def _get_files_from_dir(self, path: str):
        yield from []


def test_reqs_base_finder_find():
    config = Config()
    finder = DummyReqsFinder(config)
    
    # Test when not enabled (covers line 276-277)
    finder.enabled = False
    assert finder.find("requests") is None
    
    # Re-enable and test empty module name (covers line 281-282)
    finder.enabled = True
    assert finder.find("") is None
    
    # Test when module_name matches self.names (covers lines 284-286)
    finder.names = {"requests", "django"}
    assert finder.find("Requests.compat") == "THIRDPARTY"
    
    # Test when module_name does not match self.names (covers line 287)
    assert finder.find("unknown_module") is None
