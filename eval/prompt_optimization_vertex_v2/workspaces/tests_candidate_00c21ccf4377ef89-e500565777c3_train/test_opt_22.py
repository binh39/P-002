# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

from collections.abc import Iterator
from isort import sections
from isort.deprecated.finders import ReqsBaseFinder
from isort.settings import Config


class ConcreteReqsFinder(ReqsBaseFinder):
    def _get_names(self, path: str) -> Iterator[str]:
        return iter([])

    def _get_files_from_dir(self, path: str) -> Iterator[str]:
        return iter([])


def test_reqs_base_finder_not_enabled():
    config = Config()
    finder = ConcreteReqsFinder(config)
    finder.enabled = False
    
    # Should return None when not enabled (line 276-277)
    assert finder.find("some_module") is None


def test_reqs_base_finder_empty_module_name():
    config = Config()
    finder = ConcreteReqsFinder(config)
    finder.enabled = True
    finder.names = {"requests"}
    
    # Empty string or dot-only should partition to empty module_name (line 281-282)
    assert finder.find("") is None
    assert finder.find(".") is None


def test_reqs_base_finder_match_and_no_match():
    config = Config()
    finder = ConcreteReqsFinder(config)
    finder.enabled = True
    finder.names = {"requests", "django"}
    
    # Matching module name (case-insensitive due to lower())
    assert finder.find("Requests.compat") == sections.THIRDPARTY
    assert finder.find("DJANGO") == sections.THIRDPARTY
    
    # Non-matching module name (reaches line 287 return None)
    assert finder.find("flask.ext") is None
