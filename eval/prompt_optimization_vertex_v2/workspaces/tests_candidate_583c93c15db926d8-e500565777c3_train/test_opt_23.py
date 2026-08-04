# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

from unittest.mock import MagicMock
from collections.abc import Iterator
from isort import sections
from isort.deprecated.finders import ReqsBaseFinder
from isort.settings import Config


class DummyReqsFinder(ReqsBaseFinder):
    def _get_names(self, path: str) -> Iterator[str]:
        iter([])

    def _get_files_from_dir(self, path: str) -> Iterator[str]:
        iter([])


def test_reqs_base_finder_find():
    config = Config()

    # 1. Test when enabled is False (line 276-277)
    finder_disabled = DummyReqsFinder(config)
    finder_disabled.enabled = False
    assert finder_disabled.find("some_module") is None

    # Enable for subsequent tests
    finder = DummyReqsFinder(config)
    finder.enabled = True
    finder.names = ["requests", "click"]

    # 2. Test when module_name is empty or partitions to empty (line 281-282)
    assert finder.find("") is None
    assert finder.find(".") is None

    # 3. Test when module_name matches one in self.names (lines 284-286)
    # Also test partition and lowercase handling (lines 279-280)
    assert finder.find("Requests.submodule") == sections.THIRDPARTY
    assert finder.find("CLICK") == sections.THIRDPARTY

    # 4. Test when module_name does not match any in self.names (line 287)
    assert finder.find("unknown_module") is None
