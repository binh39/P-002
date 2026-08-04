# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

from isort.deprecated.finders import ReqsBaseFinder
from isort.settings import Config
from isort import sections


class ConcreteReqsFinder(ReqsBaseFinder):
    enabled = True
    def _get_names(self, path: str):
        return iter([])
    def _get_files_from_dir(self, path: str):
        return iter([])


def test_reqs_base_finder_find():
    config = Config()
    
    # Test when enabled is False (covers line 276-277)
    finder_disabled = ConcreteReqsFinder(config)
    finder_disabled.enabled = False
    assert finder_disabled.find("requests") is None

    # Test when enabled is True
    finder = ConcreteReqsFinder(config)
    finder.enabled = True
    finder.names = ["requests", "click"]

    # Test empty module_name after partition/lower (covers line 281-282)
    assert finder.find("") is None
    assert finder.find(".") is None

    # Test matching module name (covers lines 284-286)
    assert finder.find("Requests") == sections.THIRDPARTY
    assert finder.find("requests.compat") == sections.THIRDPARTY
    assert finder.find("click.core") == sections.THIRDPARTY

    # Test non-matching module name (covers line 287)
    assert finder.find("flask") is None
