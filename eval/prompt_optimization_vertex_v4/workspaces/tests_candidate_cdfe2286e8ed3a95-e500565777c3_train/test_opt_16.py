# file: src\sample_repo\isort\isort\deprecated\finders.py:121-165
# asked: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 136], [137, 138], [139, 140], [139, 142], [140, 139], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 150], [151, 152], [153, 154], [153, 158], [154, 153], [154, 155], [159, 160], [159, 163], [163, 0], [163, 164], [164, 163], [164, 165]]}
# gained: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 142, 147, 148, 149, 150, 151, 152, 153, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [134, 135], [136, 137], [136, 139], [137, 138], [139, 142], [142, 147], [148, 149], [150, 151], [150, 153], [151, 150], [151, 152], [153, 158], [159, 160], [163, 0], [163, 164], [164, 163], [164, 165]]}

import os
import sys
import sysconfig
import pytest
from isort.deprecated.finders import PathFinder
from isort.settings import Config




def test_path_finder_init_env_vars(tmp_path, monkeypatch):
    venv_dir = tmp_path / "venv_env"
    venv_dir.mkdir()
    site_packages = venv_dir / "lib" / "python3.9" / "site-packages"
    site_packages.mkdir(parents=True)

    conda_dir = tmp_path / "conda_env"
    conda_dir.mkdir()
    conda_site_packages = conda_dir / "lib" / "python3.9" / "site-packages"
    conda_site_packages.mkdir(parents=True)

    monkeypatch.setenv("VIRTUAL_ENV", str(venv_dir))
    monkeypatch.setenv("CONDA_PREFIX", str(conda_dir))

    # virtual_env and conda_env are not specified, so they fallback to env vars
    config = Config(settings_path=tmp_path)

    finder = PathFinder(config, path=str(tmp_path))

    assert finder.virtual_env == os.path.realpath(str(venv_dir))
    assert finder.conda_env == os.path.realpath(str(conda_dir))
    assert os.path.realpath(str(site_packages)) in [os.path.realpath(p) for p in finder.paths]
    assert os.path.realpath(str(conda_site_packages)) in [os.path.realpath(p) for p in finder.paths]
    
    # Check system paths are also included if present in sys.path
    resolved_paths = [os.path.realpath(p) for p in finder.paths]
    for p in sys.path[1:]:
        if p:
            assert os.path.realpath(p) in resolved_paths


def test_path_finder_already_in_paths(tmp_path, monkeypatch):
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    site_packages = venv_dir / "lib" / "python3.8" / "site-packages"
    site_packages.mkdir(parents=True)

    monkeypatch.setenv("VIRTUAL_ENV", str(venv_dir))
    monkeypatch.setenv("CONDA_PREFIX", str(venv_dir))

    config = Config(settings_path=tmp_path)
    
    # Pass path as site_packages so site_packages is already in self.paths when checking 'if venv_path not in self.paths'
    finder = PathFinder(config, path=str(site_packages))
    assert os.path.realpath(str(site_packages)) in [os.path.realpath(p) for p in finder.paths]
