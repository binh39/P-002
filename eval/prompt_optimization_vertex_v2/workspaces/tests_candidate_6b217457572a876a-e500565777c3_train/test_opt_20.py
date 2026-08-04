# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

import pytest
from isort import sections
from isort.deprecated.finders import ReqsBaseFinder
from isort.settings import Config


class ConcreteReqsFinder(ReqsBaseFinder):
    enabled = True

    def _get_names(self, path: str):
        return iter(self.names)

    def _get_files_from_dir(self, path: str):
        return iter([])


def test_reqs_base_finder_not_enabled():
    config = Config()
    finder = ConcreteReqsFinder(config)
    finder.enabled = False
    assert finder.find("requests") is None


def test_reqs_base_finder_empty_module_name():
    config = Config()
    finder = ConcreteReqsFinder(config)
    finder.enabled = True
    assert finder.find("") is None
    assert finder.find(".") is None


def test_reqs_base_finder_found_and_not_found():
    config = Config()
    finder = ConcreteReqsFinder(config)
    finder.enabled = True
    finder.names = {"requests", "django"}

    # Exact match
    assert finder.find("requests") == sections.THIRDPARTY
    # Partition and lowercase match
    assert finder.find("Django.utils") == sections.THIRDPARTY
    # Not found
    assert finder.find("flask") is None
