# file: src\sample_repo\isort\isort\deprecated\finders.py:121-165
# asked: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 136], [137, 138], [139, 140], [139, 142], [140, 139], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 150], [151, 152], [153, 154], [153, 158], [154, 153], [154, 155], [159, 160], [159, 163], [163, 0], [163, 164], [164, 163], [164, 165]]}
# gained: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 138], [139, 140], [139, 142], [140, 141], [142, 143], [142, 147], [143, 144], [148, 149], [150, 151], [150, 153], [151, 152], [153, 154], [153, 158], [154, 155], [159, 160], [163, 0], [163, 164], [164, 163], [164, 165]]}

import os
import sys
import sysconfig
import pytest
from isort.settings import Config
from isort.deprecated.finders import PathFinder


def test_path_finder_init_comprehensive(tmp_path, monkeypatch):
    # Set up dummy virtual environment structure
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    
    # site-packages paths
    site_packages1 = venv_dir / "lib" / "python3.9" / "site-packages"
    site_packages1.mkdir(parents=True)

    # The glob pattern for nested site packages is:
    # f"{self.virtual_env}/lib/python*/*/site-packages"
    # Notice there is a single wildcard segment between python* and site-packages,
    # e.g. lib/python3.9/site-packages/site-packages or lib/python3.9/site-packages/lib/site-packages.
    # Let's create site-packages/site-packages to match lib/python*/*/site-packages.
    nested_site_packages_dir = venv_dir / "lib" / "python3.9" / "site-packages" / "site-packages"
    nested_site_packages_dir.mkdir(parents=True)

    # venv src path
    venv_src = venv_dir / "src" / "mysPkg"
    venv_src.mkdir(parents=True)

    # Set up dummy conda environment structure
    conda_dir = tmp_path / "conda"
    conda_dir.mkdir()
    conda_site_packages = conda_dir / "lib" / "python3.10" / "site-packages"
    conda_site_packages.mkdir(parents=True)
    conda_nested_site_packages = conda_dir / "lib" / "python3.10" / "site-packages" / "site-packages"
    conda_nested_site_packages.mkdir(parents=True)

    # Clear env vars first to be deterministic, then use monkeypatch
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.delenv("CONDA_PREFIX", raising=False)

    # Test via Config virtual_env and conda_env
    config = Config(
        virtual_env=str(venv_dir),
        conda_env=str(conda_dir)
    )

    finder = PathFinder(config, path=str(tmp_path))

    assert finder.virtual_env == os.path.realpath(str(venv_dir))
    assert finder.conda_env == os.path.realpath(str(conda_dir))
    
    norm_paths = [os.path.normcase(os.path.realpath(p)) for p in finder.paths]

    assert os.path.normcase(os.path.realpath(str(site_packages1))) in norm_paths
    assert os.path.normcase(os.path.realpath(str(nested_site_packages_dir))) in norm_paths
    assert os.path.normcase(os.path.realpath(str(venv_src))) in norm_paths
    assert os.path.normcase(os.path.realpath(str(conda_site_packages))) in norm_paths
    assert os.path.normcase(os.path.realpath(str(conda_nested_site_packages))) in norm_paths
    assert finder.stdlib_lib_prefix in norm_paths


def test_path_finder_env_vars(tmp_path, monkeypatch):
    venv_dir = tmp_path / "venv_env"
    venv_dir.mkdir()
    (venv_dir / "lib" / "python3.8" / "site-packages").mkdir(parents=True)

    conda_dir = tmp_path / "conda_env"
    conda_dir.mkdir()
    (conda_dir / "lib" / "python3.8" / "site-packages").mkdir(parents=True)

    monkeypatch.setenv("VIRTUAL_ENV", str(venv_dir))
    monkeypatch.setenv("CONDA_PREFIX", str(conda_dir))

    # Config without explicit virtual_env/conda_env so it falls back to os.environ
    config = Config()
    finder = PathFinder(config, path=str(tmp_path))

    assert finder.virtual_env == os.path.realpath(str(venv_dir))
    assert finder.conda_env == os.path.realpath(str(conda_dir))


def test_path_finder_deduplication(tmp_path):
    config = Config()
    stdlib = os.path.normcase(sysconfig.get_paths()["stdlib"])
    
    finder = PathFinder(config, path=str(tmp_path))
    assert finder.paths.count(stdlib) == 1
    
    if len(sys.path) > 1:
        sys_path_item = sys.path[1]
        assert finder.paths.count(sys_path_item) == 1
