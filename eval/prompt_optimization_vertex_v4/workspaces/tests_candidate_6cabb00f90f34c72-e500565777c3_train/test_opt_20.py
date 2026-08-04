# file: src\sample_repo\isort\isort\deprecated\finders.py:121-165
# asked: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 136], [137, 138], [139, 140], [139, 142], [140, 139], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 150], [151, 152], [153, 154], [153, 158], [154, 153], [154, 155], [159, 160], [159, 163], [163, 0], [163, 164], [164, 163], [164, 165]]}
# gained: {"lines": [121, 122, 125, 126, 127, 130, 131, 133, 134, 147, 148, 158, 159, 160, 163, 164, 165], "branches": [[131, 133], [134, 147], [148, 158], [159, 160], [163, 0], [163, 164], [164, 163], [164, 165]]}

import os
import sys
import sysconfig
import pytest
from isort.settings import Config
from isort.deprecated.finders import PathFinder




def test_path_finder_no_envs(tmp_path, monkeypatch):
    # Test path finder when VIRTUAL_ENV and CONDA_PREFIX are not set and config doesn't have them either
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.delenv("CONDA_PREFIX", raising=False)

    config = Config(settings_path=tmp_path)
    finder = PathFinder(config, path=str(tmp_path))

    assert not finder.virtual_env
    assert finder.virtual_env_src == ""
    assert not finder.conda_env
    stdlib_path = os.path.normcase(sysconfig.get_paths()["stdlib"])
    assert stdlib_path in finder.paths
