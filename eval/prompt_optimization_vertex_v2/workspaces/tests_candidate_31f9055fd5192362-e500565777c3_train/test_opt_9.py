# file: src\sample_repo\isort\isort\deprecated\finders.py:121-165
# asked: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 136], [137, 138], [139, 140], [139, 142], [140, 139], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 150], [151, 152], [153, 154], [153, 158], [154, 153], [154, 155], [159, 160], [159, 163], [163, 0], [163, 164], [164, 163], [164, 165]]}
# gained: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 142, 147, 148, 149, 150, 151, 152, 153, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [134, 135], [136, 137], [136, 139], [137, 138], [139, 142], [142, 147], [148, 149], [150, 151], [150, 153], [151, 152], [153, 158], [159, 160], [163, 0], [163, 164], [164, 163], [164, 165]]}

import os
import sys
import sysconfig
import tempfile
import pytest
from isort.settings import Config
from isort.deprecated.finders import PathFinder




def test_path_finder_env_vars_fallback(monkeypatch):
    # Test fallback to os.environ for VIRTUAL_ENV and CONDA_PREFIX when not set in config
    with tempfile.TemporaryDirectory() as tmpdir:
        venv_dir = os.path.join(tmpdir, "env_venv")
        venv_sp = os.path.normcase(os.path.realpath(os.path.join(venv_dir, "lib", "python3.8", "site-packages")))
        os.makedirs(venv_sp, exist_ok=True)

        conda_dir = os.path.join(tmpdir, "env_conda")
        conda_sp = os.path.normcase(os.path.realpath(os.path.join(conda_dir, "lib", "python3.8", "site-packages")))
        os.makedirs(conda_sp, exist_ok=True)

        monkeypatch.setenv("VIRTUAL_ENV", venv_dir)
        monkeypatch.setenv("CONDA_PREFIX", conda_dir)

        config = Config()
        finder = PathFinder(config, path=tmpdir)
        norm_paths = [os.path.normcase(p) for p in finder.paths]

        assert finder.virtual_env == os.path.realpath(venv_dir)
        assert finder.conda_env == os.path.realpath(conda_dir)
        assert venv_sp in norm_paths
        assert conda_sp in norm_paths
