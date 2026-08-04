# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

from isort.deprecated.finders import ReqsBaseFinder
from isort.settings import Config
from isort import sections

class DummyReqsFinder(ReqsBaseFinder):
    enabled = True
    def _get_names(self, path: str):
        yield "foo"
    def _get_files_from_dir(self, path: str):
        return iter([])

def test_reqs_base_finder_find():
    config = Config()
    finder = DummyReqsFinder(config)
    finder.enabled = False
    
    # Test when not enabled (line 276-277)
    assert finder.find("foo") is None

    # Re-enable for subsequent checks
    finder.enabled = True
    finder.names = ["foo", "bar"]

    # Test empty module_name after partition/lower (line 281-282)
    assert finder.find("") is None
    assert finder.find(".") is None

    # Test matching name returning THIRDPARTY (line 284-286)
    assert finder.find("FOO") == sections.THIRDPARTY
    assert finder.find("foo.submodule") == sections.THIRDPARTY

    # Test non-matching name returning None (line 287)
    assert finder.find("baz") is None
