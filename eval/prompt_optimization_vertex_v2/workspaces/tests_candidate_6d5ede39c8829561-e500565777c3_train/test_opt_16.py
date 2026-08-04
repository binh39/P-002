# file: src\sample_repo\isort\isort\deprecated\finders.py:121-165
# asked: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 136], [137, 138], [139, 140], [139, 142], [140, 139], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 150], [151, 152], [153, 154], [153, 158], [154, 153], [154, 155], [159, 160], [159, 163], [163, 0], [163, 164], [164, 163], [164, 165]]}
# gained: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 142, 147, 148, 149, 150, 151, 152, 153, 158, 159, 160, 163, 164], "branches": [[131, 132], [134, 135], [136, 137], [136, 139], [137, 138], [139, 142], [142, 147], [148, 149], [150, 151], [150, 153], [151, 152], [153, 158], [159, 160], [163, 0], [163, 164], [164, 163]]}

import os
import sys
import sysconfig
import tempfile
import pytest
from isort.deprecated.finders import PathFinder
from isort.settings import Config




def test_path_finder_already_in_paths(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        venv_dir = os.path.join(tmpdir, "venv")
        os.makedirs(venv_dir)
        py_version_dir = os.path.join(venv_dir, "lib", "python3.10")
        os.makedirs(py_version_dir)
        site_packages = os.path.join(py_version_dir, "site-packages")
        os.makedirs(site_packages)

        conda_dir = os.path.join(tmpdir, "conda")
        os.makedirs(conda_dir)
        conda_py_dir = os.path.join(conda_dir, "lib", "python3.10")
        os.makedirs(conda_py_dir)
        conda_site_packages = os.path.join(conda_py_dir, "site-packages")
        os.makedirs(conda_site_packages)

        config = Config(virtual_env=venv_dir, conda_env=conda_dir)
        
        root_dir = os.path.abspath(".")
        monkeypatch.setattr(sys, "path", [sys.path[0], root_dir])
        
        finder = PathFinder(config, path=".")
        assert root_dir in finder.paths
