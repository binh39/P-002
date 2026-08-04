# file: src\sample_repo\isort\isort\deprecated\finders.py:121-165
# asked: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 136], [137, 138], [139, 140], [139, 142], [140, 139], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 150], [151, 152], [153, 154], [153, 158], [154, 153], [154, 155], [159, 160], [159, 163], [163, 0], [163, 164], [164, 163], [164, 165]]}
# gained: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 138], [139, 142], [142, 143], [142, 147], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 152], [153, 158], [159, 160], [163, 0], [163, 164], [164, 163], [164, 165]]}

import os
import sys
import sysconfig
import pytest
from isort.deprecated.finders import PathFinder
from isort.settings import Config


def test_path_finder_init_comprehensive(tmp_path):
    # Setup mock virtual env and conda env structures within tmp_path
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    
    # Create site-packages and nested site-packages and src dirs for virtual env
    site_packages = venv_dir / "lib" / "python3.9" / "site-packages"
    site_packages.mkdir(parents=True)
    
    nested_site_packages = venv_dir / "lib" / "python3.9" / "site-packages" / "nested"
    nested_site_packages.mkdir(parents=True)
    
    venv_src_sub = venv_dir / "src" / "mysubdir"
    venv_src_sub.mkdir(parents=True)
    
    # Create conda env structures
    conda_dir = tmp_path / "conda"
    conda_dir.mkdir()
    conda_site_packages = conda_dir / "lib" / "python3.9" / "site-packages"
    conda_site_packages.mkdir(parents=True)
    
    conda_nested_site_packages = conda_dir / "lib" / "python3.9" / "site-packages" / "conda_nested"
    conda_nested_site_packages.mkdir(parents=True)

    # Test case 1: virtual_env and conda_env supplied via Config, 
    # and ensuring all branches (already in paths vs not in paths, isdir checks) are hit.
    config = Config(
        virtual_env=str(venv_dir),
        conda_env=str(conda_dir)
    )

    finder = PathFinder(config, path=str(tmp_path))
    
    assert finder.virtual_env == os.path.realpath(str(venv_dir))
    assert finder.conda_env == os.path.realpath(str(conda_dir))
    
    # Paths returned by glob/realpath might have case normalization or slash differences on Windows
    real_site_packages = os.path.realpath(str(site_packages))
    assert any(os.path.realpath(p) == real_site_packages for p in finder.paths)
    
    real_conda_site_packages = os.path.realpath(str(conda_site_packages))
    assert any(os.path.realpath(p) == real_conda_site_packages for p in finder.paths)
    
    # Test adding duplicate paths to hit "not in self.paths" False branches by passing a path already in finder.paths
    # or instantiating with config pointing to an already included path or similar.
    # Also test environment variables fallback (VIRTUAL_ENV and CONDA_PREFIX)
    old_venv = os.environ.get("VIRTUAL_ENV")
    old_conda = os.environ.get("CONDA_PREFIX")
    try:
        os.environ["VIRTUAL_ENV"] = str(venv_dir)
        os.environ["CONDA_PREFIX"] = str(conda_dir)
        
        config_env = Config()
        finder_env = PathFinder(config_env, path=str(tmp_path))
        assert finder_env.virtual_env == os.path.realpath(str(venv_dir))
        assert finder_env.conda_env == os.path.realpath(str(conda_dir))
    finally:
        if old_venv is not None:
            os.environ["VIRTUAL_ENV"] = old_venv
        else:
            os.environ.pop("VIRTUAL_ENV", None)
            
        if old_conda is not None:
            os.environ["CONDA_PREFIX"] = old_conda
        else:
            os.environ.pop("CONDA_PREFIX", None)
            
    # Test when virtual_env and conda_env are empty/None
    config_empty = Config(virtual_env="", conda_env="")
    old_venv = os.environ.pop("VIRTUAL_ENV", None)
    old_conda = os.environ.pop("CONDA_PREFIX", None)
    try:
        finder_empty = PathFinder(config_empty, path=str(tmp_path))
        assert not finder_empty.virtual_env
        assert finder_empty.conda_env == ""
    finally:
        if old_venv is not None:
            os.environ["VIRTUAL_ENV"] = old_venv
        if old_conda is not None:
            os.environ["CONDA_PREFIX"] = old_conda
