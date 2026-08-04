# file: src\sample_repo\isort\isort\deprecated\finders.py:121-165
# asked: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 136], [137, 138], [139, 140], [139, 142], [140, 139], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 150], [151, 152], [153, 154], [153, 158], [154, 153], [154, 155], [159, 160], [159, 163], [163, 0], [163, 164], [164, 163], [164, 165]]}
# gained: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 138], [139, 140], [139, 142], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 152], [153, 158], [159, 160], [163, 0], [163, 164], [164, 163], [164, 165]]}

import os
import sys
import sysconfig
import pytest
from isort.settings import Config
from isort.deprecated.finders import PathFinder


def test_path_finder_init_comprehensive(tmp_path):
    # Setup mock virtual environment structure
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    
    # Create site-packages paths for venv
    venv_site1 = venv_dir / "lib" / "python3.10" / "site-packages"
    venv_site1.mkdir(parents=True)
    
    # nested venv site-packages: lib/python3.10/site-packages/something or extras/site-packages
    nested_venv_path2 = venv_dir / "lib" / "python3.10" / "extras" / "site-packages"
    nested_venv_path2.mkdir(parents=True)

    # venv src sub directory
    venv_src_sub = venv_dir / "src" / "pkgA"
    venv_src_sub.mkdir(parents=True)
    venv_src_file = venv_dir / "src" / "file.txt"
    venv_src_file.write_text("hello")

    # Setup mock conda environment structure
    conda_dir = tmp_path / "conda"
    conda_dir.mkdir()
    conda_site1 = conda_dir / "lib" / "python3.10" / "site-packages"
    conda_site1.mkdir(parents=True)

    # Configure Config with virtual_env and conda_env explicitly set
    config = Config(virtual_env=str(venv_dir), conda_env=str(conda_dir))

    # Test initialization with custom path
    root_path = tmp_path / "root"
    root_path.mkdir()

    finder = PathFinder(config, path=str(root_path))

    # Assertions to ensure all branches and lines (121-165) are executed and paths are added correctly
    assert finder.virtual_env == os.path.realpath(str(venv_dir))
    assert finder.virtual_env_src == f"{finder.virtual_env}/src/"
    
    # glob paths use os.path.realpath or os.path.abspath semantics matching glob / os.path operations
    # Normalize paths via os.path.normpath or os.path.realpath for robust comparison across platforms
    paths_normalized = [os.path.normpath(p) for p in finder.paths]

    assert os.path.normpath(str(venv_site1)) in paths_normalized
    assert os.path.normpath(str(nested_venv_path2)) in paths_normalized
    assert os.path.normpath(str(venv_src_sub)) in paths_normalized
    assert os.path.normpath(str(venv_src_file)) not in paths_normalized  # because it's a file, not a dir

    assert finder.conda_env == os.path.realpath(str(conda_dir))
    assert os.path.normpath(str(conda_site1)) in paths_normalized

    stdlib = os.path.normcase(sysconfig.get_paths()["stdlib"])
    assert stdlib in paths_normalized

    for sp in sys.path[1:]:
        assert os.path.normpath(sp) in paths_normalized


def test_path_finder_env_fallback(monkeypatch, tmp_path):
    venv_dir = tmp_path / "env_venv"
    venv_dir.mkdir()
    conda_dir = tmp_path / "env_conda"
    conda_dir.mkdir()

    monkeypatch.setenv("VIRTUAL_ENV", str(venv_dir))
    monkeypatch.setenv("CONDA_PREFIX", str(conda_dir))

    config = Config()  # virtual_env and conda_env not set in config, should fall back to env vars
    finder = PathFinder(config, path=str(tmp_path))

    assert finder.virtual_env == os.path.realpath(str(venv_dir))
    assert finder.conda_env == os.path.realpath(str(conda_dir))


def test_path_finder_no_env(monkeypatch, tmp_path):
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.delenv("CONDA_PREFIX", raising=False)

    config = Config()
    finder = PathFinder(config, path=str(tmp_path))

    assert not finder.virtual_env
    assert finder.conda_env == ""
