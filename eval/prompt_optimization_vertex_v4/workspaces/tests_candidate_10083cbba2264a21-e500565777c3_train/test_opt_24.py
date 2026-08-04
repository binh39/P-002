# file: src\sample_repo\isort\isort\deprecated\finders.py:121-165
# asked: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 136], [137, 138], [139, 140], [139, 142], [140, 139], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 150], [151, 152], [153, 154], [153, 158], [154, 153], [154, 155], [159, 160], [159, 163], [163, 0], [163, 164], [164, 163], [164, 165]]}
# gained: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 142, 147, 148, 149, 150, 151, 152, 153, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 138], [139, 142], [142, 147], [148, 149], [148, 158], [150, 151], [150, 153], [151, 152], [153, 158], [159, 160], [163, 0], [163, 164], [164, 163], [164, 165]]}

import os
import sys
import sysconfig
from isort.deprecated.finders import PathFinder
from isort.settings import Config




def test_path_finder_env_vars_fallback(tmp_path, monkeypatch):
    monkeypatch.delenv("CONDA_PREFIX", raising=False)
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)

    venv_dir = tmp_path / "env_venv"
    venv_dir.mkdir()
    site_packages = venv_dir / "lib" / "python3.9" / "site-packages"
    site_packages.mkdir(parents=True)

    conda_dir = tmp_path / "env_conda"
    conda_dir.mkdir()
    conda_site_packages = conda_dir / "lib" / "python3.9" / "site-packages"
    conda_site_packages.mkdir(parents=True)

    monkeypatch.setenv("VIRTUAL_ENV", str(venv_dir))
    monkeypatch.setenv("CONDA_PREFIX", str(conda_dir))

    config = Config()
    finder = PathFinder(config, path=str(tmp_path))

    assert finder.virtual_env == os.path.realpath(str(venv_dir))
    assert finder.conda_env == os.path.realpath(str(conda_dir))
    
    resolved_paths = [os.path.realpath(p) for p in finder.paths]
    assert os.path.realpath(str(site_packages)) in resolved_paths
    assert os.path.realpath(str(conda_site_packages)) in resolved_paths


def test_path_finder_no_env(tmp_path, monkeypatch):
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.delenv("CONDA_PREFIX", raising=False)

    config = Config()
    finder = PathFinder(config, path=str(tmp_path))
    assert finder.virtual_env is None
    assert finder.conda_env == ""
