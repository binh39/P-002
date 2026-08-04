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
    
    # Test case 1: self.enabled is False (default for base or when disabled)
    finder_disabled = DummyReqsFinder(config)
    finder_disabled.enabled = False
    assert finder_disabled.find("requests") is None

    # Enable finder for subsequent tests
    finder = DummyReqsFinder(config)
    finder.enabled = True
    finder.names = ["requests", "numpy"]

    # Test case 2: Empty module_name or module_name resulting in empty after partition
    assert finder.find("") is None
    assert finder.find(".") is None

    # Test case 3: Matching module name (exact or with submodules/case insensitivity)
    assert finder.find("Requests") == sections.THIRDPARTY
    assert finder.find("numpy.linalg") == sections.THIRDPARTY

    # Test case 4: Non-matching module name
    assert finder.find("os") is None
