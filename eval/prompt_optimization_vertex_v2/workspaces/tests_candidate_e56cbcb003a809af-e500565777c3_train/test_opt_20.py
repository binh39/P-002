# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

import pytest
from isort import sections
from isort.deprecated.finders import ReqsBaseFinder
from isort.settings import Config


class DummyReqsFinder(ReqsBaseFinder):
    def _get_names(self, path: str):
        return iter([])

    def _get_files_from_dir(self, path: str):
        return iter([])


def test_reqs_base_finder_find():
    config = Config()

    # 1. Test when enabled is False (hits lines 276-277)
    finder_disabled = DummyReqsFinder(config)
    finder_disabled.enabled = False
    assert finder_disabled.find("some_module") is None

    # 2. Test when enabled is True, but module_name is empty after partition/lower (hits lines 281-282)
    finder_enabled = DummyReqsFinder(config)
    finder_enabled.enabled = True
    finder_enabled.names = ["requests"]
    assert finder_enabled.find("") is None
    assert finder_enabled.find(".") is None

    # 3. Test when module matches one in self.names (hits lines 284-286)
    assert finder_enabled.find("Requests.compat") == sections.THIRDPARTY

    # 4. Test when module does not match any in self.names (hits line 287)
    assert finder_enabled.find("numpy.core") is None
