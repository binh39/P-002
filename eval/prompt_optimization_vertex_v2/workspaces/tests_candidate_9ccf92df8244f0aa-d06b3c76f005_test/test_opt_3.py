# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

from collections.abc import Iterable
from isort import sections
from isort.deprecated.finders import ReqsBaseFinder
from isort.settings import Config


class DummyReqsFinder(ReqsBaseFinder):
    def _get_names(self, path: str) -> Iterable[str]:
        return []

    def _get_files_from_dir(self, path: str) -> Iterable[str]:
        return []


def test_reqs_base_finder_find():
    config = Config()
    finder = DummyReqsFinder(config)

    # 1. Test when not enabled (line 276-277)
    finder.enabled = False
    assert finder.find("any_module") is None

    # Enable finder for subsequent tests
    finder.enabled = True
    finder.names = ["requests", "click"]

    # 2. Test empty module name or partition resulting in empty module name (line 281-282)
    assert finder.find("") is None
    assert finder.find(".") is None

    # 3. Test matching module name in self.names (lines 284-286)
    assert finder.find("requests") == sections.THIRDPARTY
    # Test case insensitivity and submodules (lines 279-280)
    assert finder.find("CLICK.utils") == sections.THIRDPARTY

    # 4. Test non-matching module name (line 287)
    assert finder.find("flask") is None
