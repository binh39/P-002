# file: src\sample_repo\isort\isort\deprecated\finders.py:121-165
# asked: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 136], [137, 138], [139, 140], [139, 142], [140, 139], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 150], [151, 152], [153, 154], [153, 158], [154, 153], [154, 155], [159, 160], [159, 163], [163, 0], [163, 164], [164, 163], [164, 165]]}
# gained: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 142, 147, 148, 149, 150, 151, 152, 153, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [134, 135], [136, 137], [136, 139], [137, 138], [139, 142], [142, 147], [148, 149], [150, 151], [150, 153], [151, 152], [153, 158], [159, 160], [163, 0], [163, 164], [164, 163], [164, 165]]}

import os
import sys
import sysconfig
import tempfile
import pathlib
import pytest
from isort.settings import Config
from isort.deprecated.finders import PathFinder


@pytest.fixture
def custom_tmp_path():
    d = tempfile.TemporaryDirectory()
    yield pathlib.Path(d.name)
    try:
        d.cleanup()
    except PermissionError:
        pass




def test_path_finder_already_existing_paths(custom_tmp_path):
    venv_dir = custom_tmp_path / "venv"
    venv_dir.mkdir()
    sp1 = venv_dir / "lib" / "python3.10" / "site-packages"
    sp1.mkdir(parents=True)

    conda_dir = custom_tmp_path / "conda"
    conda_dir.mkdir()
    conda_sp1 = conda_dir / "lib" / "python3.9" / "site-packages"
    conda_sp1.mkdir(parents=True)

    config = Config(virtual_env=str(venv_dir), conda_env=str(conda_dir))

    old_sys_path = sys.path[:]
    try:
        sys.path.insert(1, str(sp1))
        sys.path.insert(1, os.path.normcase(sysconfig.get_paths()["stdlib"]))
        
        finder = PathFinder(config, path=str(custom_tmp_path))
        assert finder.paths.count(str(sp1)) == 1
    finally:
        sys.path[:] = old_sys_path
