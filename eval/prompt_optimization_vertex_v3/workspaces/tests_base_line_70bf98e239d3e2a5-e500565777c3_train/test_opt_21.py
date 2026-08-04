# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

import pytest
from isort import sections
from isort.deprecated.finders import ReqsBaseFinder
from isort.settings import Config


class DummyReqsFinder(ReqsBaseFinder):
    enabled = True

    def _get_names(self, path: str):
        return iter([])

    def _get_files_from_dir(self, path: str):
        return iter([])


def test_reqs_base_finder_find():
    config = Config()
    finder = DummyReqsFinder(config)

    # Test when self.enabled is False
    finder.enabled = False
    assert finder.find("requests") is None

    # Test when self.enabled is True again
    finder.enabled = True
    finder.names = {"requests", "django"}

    # Test when module_name is empty after partition
    assert finder.find("") is None
    assert finder.find(".") is None

    # Test when module_name matches one in self.names (exact match and submodule partition, and case insensitivity)
    assert finder.find("Requests") == sections.THIRDPARTY
    assert finder.find("django.http") == sections.THIRDPARTY

    # Test when module_name does not match any in self.names
    assert finder.find("unknown_module") is None
