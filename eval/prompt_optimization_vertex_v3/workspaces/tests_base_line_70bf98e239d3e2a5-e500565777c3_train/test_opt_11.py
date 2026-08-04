# file: src\sample_repo\isort\isort\deprecated\finders.py:121-165
# asked: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 136], [137, 138], [139, 140], [139, 142], [140, 139], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 150], [151, 152], [153, 154], [153, 158], [154, 153], [154, 155], [159, 160], [159, 163], [163, 0], [163, 164], [164, 163], [164, 165]]}
# gained: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 138], [139, 140], [139, 142], [140, 141], [142, 143], [142, 147], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 152], [153, 154], [153, 158], [154, 155], [159, 160], [163, 0], [163, 164], [164, 163], [164, 165]]}

import os
import sys
import sysconfig
from isort.deprecated.finders import PathFinder
from isort.settings import Config


def test_path_finder_init_full_branches(tmp_path, monkeypatch):
    # Setup temporary directory structure to exercise virtual env and conda paths
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    
    # Create site-packages and nested site-packages under venv matching glob pattern:
    # lib/python*/*/site-packages means lib/python<version>/<something>/site-packages
    lib_py_dir = venv_dir / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}"
    site_packages = lib_py_dir / "site-packages"
    site_packages.mkdir(parents=True)

    nested_site_packages = lib_py_dir / "site-packages-extras" / "site-packages"
    nested_site_packages.mkdir(parents=True)

    # Create src subdirectory and a dummy directory inside it under venv
    venv_src = venv_dir / "src"
    venv_src.mkdir()
    dummy_src_sub = venv_src / "dummy_package"
    dummy_src_sub.mkdir()

    # Setup conda env structure similarly or separately
    conda_dir = tmp_path / "conda"
    conda_dir.mkdir()
    conda_lib_py = conda_dir / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}"
    conda_site_packages = conda_lib_py / "site-packages"
    conda_site_packages.mkdir(parents=True)
    conda_nested = conda_lib_py / "site-packages-extras" / "site-packages"
    conda_nested.mkdir(parents=True)

    # Configure Config with virtual_env and conda_env
    config = Config(virtual_env=str(venv_dir), conda_env=str(conda_dir))

    # Also test environment variables branch by setting VIRTUAL_ENV and CONDA_PREFIX
    # (Though config takes precedence, we can also test when config attributes are empty)
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.delenv("CONDA_PREFIX", raising=False)

    finder = PathFinder(config, path=str(tmp_path / "root"))

    assert finder.virtual_env == os.path.realpath(str(venv_dir))
    assert finder.virtual_env_src == f"{finder.virtual_env}/src/"
    assert os.path.normcase(str(site_packages)) in [os.path.normcase(p) for p in finder.paths]
    assert os.path.normcase(str(nested_site_packages)) in [os.path.normcase(p) for p in finder.paths]
    assert os.path.normcase(str(dummy_src_sub)) in [os.path.normcase(p) for p in finder.paths]

    assert finder.conda_env == os.path.realpath(str(conda_dir))
    assert os.path.normcase(str(conda_site_packages)) in [os.path.normcase(p) for p in finder.paths]
    assert os.path.normcase(str(conda_nested)) in [os.path.normcase(p) for p in finder.paths]

    # Test when virtual_env and conda_env come from environment variables via config fallback
    config_empty = Config()
    monkeypatch.setenv("VIRTUAL_ENV", str(venv_dir))
    monkeypatch.setenv("CONDA_PREFIX", str(conda_dir))

    finder_env = PathFinder(config_empty, path=str(tmp_path / "root2"))
    assert finder_env.virtual_env == os.path.realpath(str(venv_dir))
    assert finder_env.conda_env == os.path.realpath(str(conda_dir))

    # Test when virtual_env / conda_env are completely absent/empty
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.delenv("CONDA_PREFIX", raising=False)
    config_no_env = Config()
    finder_no_env = PathFinder(config_no_env, path=str(tmp_path / "root3"))
    assert not finder_no_env.virtual_env
    assert finder_no_env.conda_env == ""

    # Ensure stdlib and system paths are added/checked
    stdlib_path = os.path.normcase(sysconfig.get_paths()["stdlib"])
    assert stdlib_path in finder_no_env.paths
    for sp in sys.path[1:]:
        if sp:
            assert sp in finder_no_env.paths
