# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

from unittest.mock import MagicMock
from isort import sections
from isort.deprecated.finders import ReqsBaseFinder
from isort.settings import Config


class ConcreteReqsFinder(ReqsBaseFinder):
    """Concrete subclass of ReqsBaseFinder for testing purposes."""
    
    def _get_names(self, path: str):
        return iter([])

    def _get_files_from_dir(self, path: str):
        return iter([])


def test_reqs_base_finder_find_coverage():
    config = MagicMock(spec=Config)
    finder = ConcreteReqsFinder(config)

    # 1. Test when not enabled (line 276 -> returns None)
    finder.enabled = False
    assert finder.find("some_module") is None

    # Enable finder for remaining checks
    finder.enabled = True

    # 2. Test when module_name is empty or just dots resulting in empty module_name (line 281 -> returns None)
    assert finder.find("") is None
    assert finder.find(".") is None

    # Set up names for matching
    finder.names = ["foo", "bar"]

    # 3. Test when module_name matches one of self.names (line 285-286 -> returns THIRDPARTY)
    assert finder.find("FOO") == sections.THIRDPARTY
    assert finder.find("bar.submodule") == sections.THIRDPARTY

    # 4. Test when module_name does not match any name (line 284 loop finishes, line 287 -> returns None)
    assert finder.find("baz") is None
