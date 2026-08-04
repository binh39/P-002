# file: src\sample_repo\isort\isort\deprecated\finders.py:121-165
# asked: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 136], [137, 138], [139, 140], [139, 142], [140, 139], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 150], [151, 152], [153, 154], [153, 158], [154, 153], [154, 155], [159, 160], [159, 163], [163, 0], [163, 164], [164, 163], [164, 165]]}
# gained: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 138], [139, 140], [139, 142], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 152], [153, 154], [153, 158], [154, 155], [159, 160], [163, 0], [163, 164], [164, 163], [164, 165]]}

import os
import sys
import sysconfig
import pytest
from isort.settings import Config
from isort.deprecated.finders import PathFinder


def test_path_finder_init_basic(tmp_path):
    # Test basic initialization without virtual_env or conda_env set via config or env vars,
    # and ensuring stdlib and system paths are correctly evaluated and appended/checked.
    old_virtual_env = os.environ.get("VIRTUAL_ENV")
    old_conda_prefix = os.environ.get("CONDA_PREFIX")
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]
    if "CONDA_PREFIX" in os.environ:
        del os.environ["CONDA_PREFIX"]

    try:
        config = Config()
        finder = PathFinder(config, path=str(tmp_path))
        assert os.path.abspath(str(tmp_path)) in finder.paths
        assert f"{os.path.abspath(str(tmp_path))}/src" in finder.paths
        assert finder.virtual_env is None
        assert finder.conda_env == ""
    finally:
        if old_virtual_env is not None:
            os.environ["VIRTUAL_ENV"] = old_virtual_env
        if old_conda_prefix is not None:
            os.environ["CONDA_PREFIX"] = old_conda_prefix


def test_path_finder_init_virtual_env(tmp_path):
    # Test initialization with a simulated virtual environment structure
    venv_dir = tmp_path / "my_venv"
    venv_dir.mkdir()
    
    # Create matching glob directories for venv
    # 1. lib/pythonX.Y/site-packages
    site_packages = venv_dir / "lib" / "python3.9" / "site-packages"
    site_packages.mkdir(parents=True)

    # 2. lib/pythonX.Y/extras/site-packages (matches lib/python*/*/site-packages)
    nested_dir = venv_dir / "lib" / "python3.9" / "extras" / "site-packages"
    nested_dir.mkdir(parents=True)

    # 3. src/*
    src_sub = venv_dir / "src" / "package_a"
    src_sub.mkdir(parents=True)

    config = Config(virtual_env=str(venv_dir))
    finder = PathFinder(config, path=str(tmp_path))

    assert finder.virtual_env == os.path.realpath(str(venv_dir))
    assert finder.virtual_env_src == f"{finder.virtual_env}/src/"
    # PathFinder uses glob which might return paths with OS-specific separators or norms; check realpath or normpath equality
    assert os.path.realpath(str(site_packages)) in [os.path.realpath(p) for p in finder.paths]
    assert os.path.realpath(str(nested_dir)) in [os.path.realpath(p) for p in finder.paths]
    assert os.path.realpath(str(src_sub)) in [os.path.realpath(p) for p in finder.paths]

    # Test when virtual_env is already in paths or file instead of dir for src
    file_in_src = venv_dir / "src" / "not_a_dir.txt"
    file_in_src.write_text("hello")

    finder2 = PathFinder(config, path=str(tmp_path))
    assert os.path.realpath(str(file_in_src)) not in [os.path.realpath(p) for p in finder2.paths]


def test_path_finder_init_conda_env(tmp_path):
    # Test initialization with a simulated conda environment structure
    conda_dir = tmp_path / "my_conda"
    conda_dir.mkdir()

    conda_site_packages = conda_dir / "lib" / "python3.10" / "site-packages"
    conda_site_packages.mkdir(parents=True)

    conda_nested_dir = conda_dir / "lib" / "python3.10" / "extras" / "site-packages"
    conda_nested_dir.mkdir(parents=True)

    config = Config(conda_env=str(conda_dir))
    finder = PathFinder(config, path=str(tmp_path))

    assert finder.conda_env == os.path.realpath(str(conda_dir))
    assert os.path.realpath(str(conda_site_packages)) in [os.path.realpath(p) for p in finder.paths]
    assert os.path.realpath(str(conda_nested_dir)) in [os.path.realpath(p) for p in finder.paths]


def test_path_finder_env_vars(tmp_path):
    # Test fallback to VIRTUAL_ENV and CONDA_PREFIX environment variables
    old_virtual_env = os.environ.get("VIRTUAL_ENV")
    old_conda_prefix = os.environ.get("CONDA_PREFIX")

    venv_dir = tmp_path / "env_venv"
    venv_dir.mkdir()
    conda_dir = tmp_path / "env_conda"
    conda_dir.mkdir()

    os.environ["VIRTUAL_ENV"] = str(venv_dir)
    os.environ["CONDA_PREFIX"] = str(conda_dir)

    try:
        config = Config()
        finder = PathFinder(config, path=str(tmp_path))
        assert finder.virtual_env == os.path.realpath(str(venv_dir))
        assert finder.conda_env == os.path.realpath(str(conda_dir))
    finally:
        if old_virtual_env is not None:
            os.environ["VIRTUAL_ENV"] = old_virtual_env
        else:
            del os.environ["VIRTUAL_ENV"]

        if old_conda_prefix is not None:
            os.environ["CONDA_PREFIX"] = old_conda_prefix
        else:
            del os.environ["CONDA_PREFIX"]


def test_path_finder_stdlib_and_system_paths(tmp_path):
    # Test that stdlib and sys.path entries are checked and added if not present
    config = Config()
    finder = PathFinder(config, path=str(tmp_path))

    stdlib = os.path.normcase(sysconfig.get_paths()["stdlib"])
    assert stdlib in finder.paths

    # Add a custom path to sys.path temporarily to ensure system_path branch executes and appends
    custom_sys_path = str(tmp_path / "custom_sys_path")
    sys.path.append(custom_sys_path)
    try:
        finder2 = PathFinder(config, path=str(tmp_path))
        assert custom_sys_path in finder2.paths
        
        # Test when system_path is already in paths (e.g., if root_dir or src_dir matches sys.path[1:])
        sys.path.insert(1, str(tmp_path))
        finder3 = PathFinder(config, path=str(tmp_path))
        assert str(tmp_path) in finder3.paths
    finally:
        sys.path.remove(custom_sys_path)
        if str(tmp_path) in sys.path:
            sys.path.remove(str(tmp_path))
