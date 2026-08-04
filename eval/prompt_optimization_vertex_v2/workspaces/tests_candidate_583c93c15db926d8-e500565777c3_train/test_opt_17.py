# file: src\sample_repo\isort\isort\deprecated\finders.py:121-165
# asked: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 136], [137, 138], [139, 140], [139, 142], [140, 139], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 150], [151, 152], [153, 154], [153, 158], [154, 153], [154, 155], [159, 160], [159, 163], [163, 0], [163, 164], [164, 163], [164, 165]]}
# gained: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 139, 142, 147, 148, 149, 150, 153, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 139], [139, 142], [142, 147], [148, 149], [148, 158], [150, 153], [153, 158], [159, 160], [163, 0], [163, 164], [164, 163], [164, 165]]}

import os
import sys
import sysconfig
import tempfile
from pathlib import Path
import pytest
from isort.deprecated.finders import PathFinder
from isort.settings import Config


@pytest.fixture
def custom_tmp_path():
    d = tempfile.TemporaryDirectory()
    yield Path(d.name)
    d.cleanup()




def test_path_finder_init_env_vars_and_duplicates(custom_tmp_path, monkeypatch):
    venv_dir = custom_tmp_path / "venv_env"
    venv_dir.mkdir()
    
    conda_dir = custom_tmp_path / "conda_env"
    conda_dir.mkdir()

    monkeypatch.setenv("VIRTUAL_ENV", str(venv_dir))
    monkeypatch.setenv("CONDA_PREFIX", str(conda_dir))

    stdlib = os.path.normcase(sysconfig.get_paths()["stdlib"])
    sys_path_item = sys.path[1] if len(sys.path) > 1 else str(custom_tmp_path)

    config = Config()
    finder = PathFinder(config, path=str(custom_tmp_path))

    assert finder.virtual_env == os.path.realpath(str(venv_dir))
    assert finder.conda_env == os.path.realpath(str(conda_dir))
    assert stdlib in finder.paths
    assert sys_path_item in finder.paths


def test_path_finder_no_env_vars(monkeypatch, custom_tmp_path):
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.delenv("CONDA_PREFIX", raising=False)

    config = Config(virtual_env="", conda_env="")
    finder = PathFinder(config, path=str(custom_tmp_path))

    assert not finder.virtual_env
    assert finder.conda_env == ""
    assert os.path.normcase(sysconfig.get_paths()["stdlib"]) in finder.paths
