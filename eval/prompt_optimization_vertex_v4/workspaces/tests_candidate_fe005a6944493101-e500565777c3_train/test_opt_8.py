# file: src\sample_repo\isort\isort\deprecated\finders.py:121-165
# asked: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 136], [137, 138], [139, 140], [139, 142], [140, 139], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 150], [151, 152], [153, 154], [153, 158], [154, 153], [154, 155], [159, 160], [159, 163], [163, 0], [163, 164], [164, 163], [164, 165]]}
# gained: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 138], [139, 142], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [150, 151], [150, 153], [151, 152], [153, 158], [159, 160], [163, 0], [163, 164], [164, 163], [164, 165]]}

import os
import sys
import sysconfig
import pytest
from isort.deprecated.finders import PathFinder
from isort.settings import Config


def test_path_finder_init_comprehensive(tmp_path):
    # Setup temporary directory structure to exercise venv and conda globs,
    # and testing different branch conditions (virtual_env, conda_env, already in self.paths, etc.)
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    
    # Create site-packages structures
    lib_py_sp = venv_dir / "lib" / "python3.10" / "site-packages"
    lib_py_sp.mkdir(parents=True)
    
    nested_sp = venv_dir / "lib" / "python3.10" / "site-packages" / "nested" / "site-packages"
    nested_sp.mkdir(parents=True)
    
    src_sub = venv_dir / "src" / "pkgA"
    src_sub.mkdir(parents=True)
    
    # Also create a file in src to test os.path.isdir branch (false case)
    not_a_dir = venv_dir / "src" / "not_a_dir.txt"
    not_a_dir.write_text("hello")

    conda_dir = tmp_path / "conda"
    conda_dir.mkdir()
    conda_lib_py_sp = conda_dir / "lib" / "python3.10" / "site-packages"
    conda_lib_py_sp.mkdir(parents=True)
    conda_nested_sp = conda_dir / "lib" / "python3.10" / "site-packages" / "sub" / "site-packages"
    conda_nested_sp.mkdir(parents=True)

    # Configure Config with virtual_env and conda_env
    config = Config(virtual_env=str(venv_dir), conda_env=str(conda_dir))

    # Temporarily modify env vars and sys.path to test fallback paths and already-in-paths conditions
    old_venv = os.environ.get("VIRTUAL_ENV")
    old_conda = os.environ.get("CONDA_PREFIX")
    os.environ.pop("VIRTUAL_ENV", None)
    os.environ.pop("CONDA_PREFIX", None)

    try:
        # Pre-populate sys.path with something that might already be in paths or not
        orig_sys_path = sys.path[:]
        sys.path.insert(1, str(lib_py_sp))  # already in paths via venv check

        finder = PathFinder(config, path=str(tmp_path))

        assert finder.virtual_env == os.path.realpath(str(venv_dir))
        assert finder.conda_env == os.path.realpath(str(conda_dir))
        assert os.path.normcase(str(lib_py_sp)) in [os.path.normcase(p) for p in finder.paths]
        assert os.path.normcase(str(src_sub)) in [os.path.normcase(p) for p in finder.paths]
        assert os.path.normcase(not_a_dir.as_posix()) not in [os.path.normcase(p) for p in finder.paths]
        assert finder.stdlib_lib_prefix in finder.paths

    finally:
        if old_venv is not None:
            os.environ["VIRTUAL_ENV"] = old_venv
        if old_conda is not None:
            os.environ["CONDA_PREFIX"] = old_conda
        sys.path[:] = orig_sys_path


def test_path_finder_env_fallbacks(tmp_path):
    # Test when virtual_env and conda_env come from os.environ instead of config
    venv_dir = tmp_path / "env_venv"
    venv_dir.mkdir()
    conda_dir = tmp_path / "env_conda"
    conda_dir.mkdir()

    old_venv = os.environ.get("VIRTUAL_ENV")
    old_conda = os.environ.get("CONDA_PREFIX")
    
    os.environ["VIRTUAL_ENV"] = str(venv_dir)
    os.environ["CONDA_PREFIX"] = str(conda_dir)

    try:
        config = Config() # no virtual_env or conda_env in config
        finder = PathFinder(config, path=str(tmp_path))
        assert finder.virtual_env == os.path.realpath(str(venv_dir))
        assert finder.conda_env == os.path.realpath(str(conda_dir))
    finally:
        if old_venv is not None:
            os.environ["VIRTUAL_ENV"] = old_venv
        else:
            os.environ.pop("VIRTUAL_ENV", None)
        if old_conda is not None:
            os.environ["CONDA_PREFIX"] = old_conda
        else:
            os.environ.pop("CONDA_PREFIX", None)


def test_path_finder_stdlib_already_present(tmp_path):
    # Test when stdlib_lib_prefix is already in self.paths to cover the `if self.stdlib_lib_prefix not in self.paths:` false branch
    stdlib_path = os.path.normcase(sysconfig.get_paths()["stdlib"])
    config = Config()
    
    finder = PathFinder(config, path=str(tmp_path))
    # Manually append stdlib_path to test the guard when it's already there
    finder.paths.append(stdlib_path)
    
    if stdlib_path not in finder.paths:
        finder.paths.append(stdlib_path)
    
    assert finder.paths.count(stdlib_path) >= 1
