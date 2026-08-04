# file: src\sample_repo\isort\isort\deprecated\finders.py:274-287
# asked: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}
# gained: {"lines": [274, 276, 277, 279, 280, 281, 282, 284, 285, 286, 287], "branches": [[276, 277], [276, 279], [281, 282], [281, 284], [284, 285], [284, 287], [285, 284], [285, 286]]}

from collections.abc import Iterator
from isort import sections
from isort.deprecated.finders import ReqsBaseFinder
from isort.settings import Config


class ConcreteReqsFinder(ReqsBaseFinder):
    enabled = True

    def __init__(self, config: Config, path: str = ".", names=None) -> None:
        self.config = config
        self.path = path
        self.names = names or []

    def _get_names(self, path: str) -> Iterator[str]:
        return iter([])

    def _get_files_from_dir(self, path: str) -> Iterator[str]:
        return iter([])


def test_reqs_base_finder_find():
    config = Config()

    # 1. Test when not enabled
    finder_disabled = ConcreteReqsFinder(config)
    finder_disabled.enabled = False
    assert finder_disabled.find("requests") is None

    # 2. Test when module_name is empty or partitions to empty
    finder_enabled = ConcreteReqsFinder(config, names=["requests"])
    assert finder_enabled.find("") is None
    assert finder_enabled.find(".") is None

    # 3. Test when module_name matches one in self.names (case-insensitive, partition check)
    assert finder_enabled.find("Requests.compat") == sections.THIRDPARTY
    assert finder_enabled.find("requests") == sections.THIRDPARTY

    # 4. Test when module_name does not match any in self.names
    assert finder_enabled.find("urllib") is None
