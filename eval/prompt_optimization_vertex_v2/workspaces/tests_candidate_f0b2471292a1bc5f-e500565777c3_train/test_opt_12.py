# file: src\sample_repo\isort\isort\deprecated\finders.py:121-165
# asked: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 136], [137, 138], [139, 140], [139, 142], [140, 139], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 150], [151, 152], [153, 154], [153, 158], [154, 153], [154, 155], [159, 160], [159, 163], [163, 0], [163, 164], [164, 163], [164, 165]]}
# gained: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 142, 147, 148, 149, 150, 151, 152, 153, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [134, 135], [136, 137], [136, 139], [137, 138], [139, 142], [142, 147], [148, 149], [150, 151], [150, 153], [151, 152], [153, 158], [159, 160], [163, 0], [163, 164], [164, 165]]}

import os
import sys
import sysconfig
import tempfile
import shutil
import pytest
from isort.settings import Config
from isort.deprecated.finders import PathFinder


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp()
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)




def test_path_finder_init_env_vars_and_duplicates(temp_dir, monkeypatch):
    venv_dir = os.path.join(temp_dir, "venv_env")
    os.makedirs(venv_dir, exist_ok=True)
    
    sp1 = os.path.join(venv_dir, "lib", "python3.11", "site-packages")
    os.makedirs(sp1, exist_ok=True)

    conda_dir = os.path.join(temp_dir, "conda_env")
    conda_sp1 = os.path.join(conda_dir, "lib", "python3.11", "site-packages")
    os.makedirs(conda_sp1, exist_ok=True)

    monkeypatch.setenv("VIRTUAL_ENV", venv_dir)
    monkeypatch.setenv("CONDA_PREFIX", conda_dir)

    config = Config() 
    
    stdlib_path = sysconfig.get_paths()["stdlib"]
    original_sys_path = sys.path[:]
    sys.path = [sys.path[0], stdlib_path]

    try:
        root_path2 = os.path.join(temp_dir, "root2")
        os.makedirs(root_path2, exist_ok=True)
        finder = PathFinder(config, path=root_path2)
        assert finder.virtual_env == os.path.realpath(venv_dir)
        assert finder.conda_env == os.path.realpath(conda_dir)
        assert finder.paths.count(os.path.normcase(stdlib_path)) == 1
    finally:
        sys.path = original_sys_path
