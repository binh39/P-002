# file: src\sample_repo\isort\isort\deprecated\finders.py:121-165
# asked: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 136], [137, 138], [139, 140], [139, 142], [140, 139], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 150], [151, 152], [153, 154], [153, 158], [154, 153], [154, 155], [159, 160], [159, 163], [163, 0], [163, 164], [164, 163], [164, 165]]}
# gained: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [134, 135], [136, 137], [136, 139], [137, 138], [139, 140], [139, 142], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [150, 151], [150, 153], [151, 152], [153, 154], [153, 158], [154, 155], [159, 160], [163, 0], [163, 164], [164, 163], [164, 165]]}

import os
import sys
import sysconfig
import tempfile
import pytest
from isort.deprecated.finders import PathFinder
from isort.settings import Config


@pytest.fixture
def custom_tmp_dir():
    d = tempfile.TemporaryDirectory()
    try:
        yield d.name
    finally:
        d.cleanup()


def test_path_finder_init_comprehensive(custom_tmp_dir, monkeypatch):
    root_base = os.path.realpath(custom_tmp_dir)
    venv_dir = os.path.join(root_base, "venv")
    os.makedirs(venv_dir, exist_ok=True)
    
    # 1. venv site-packages (standard & nested)
    lib_py_dir = os.path.join(venv_dir, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}")
    site_packages = os.path.join(lib_py_dir, "site-packages")
    os.makedirs(site_packages, exist_ok=True)

    nested_parent = os.path.join(lib_py_dir, "site-packages-extra")
    nested_site_packages2 = os.path.join(nested_parent, "site-packages")
    os.makedirs(nested_site_packages2, exist_ok=True)

    # 2. venv src dirs
    src_parent = os.path.join(venv_dir, "src")
    valid_src_sub = os.path.join(src_parent, "pkg1")
    os.makedirs(valid_src_sub, exist_ok=True)
    invalid_src_file = os.path.join(src_parent, "file.txt")
    with open(invalid_src_file, "w") as f:
        f.write("hello")

    # Setup conda environment structure
    conda_dir = os.path.join(root_base, "conda")
    conda_lib_py = os.path.join(conda_dir, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}")
    conda_site_packages = os.path.join(conda_lib_py, "site-packages")
    os.makedirs(conda_site_packages, exist_ok=True)

    conda_nested_parent = os.path.join(conda_lib_py, "extra")
    conda_nested_site_packages = os.path.join(conda_nested_parent, "site-packages")
    os.makedirs(conda_nested_site_packages, exist_ok=True)

    # Ensure environment variables are clear or set via monkeypatch
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.delenv("CONDA_PREFIX", raising=False)

    config = Config(virtual_env=venv_dir, conda_env=conda_dir)

    stdlib_path = os.path.normcase(sysconfig.get_paths()["stdlib"])
    
    custom_sys_path = os.path.join(root_base, "custom_sys_path")
    os.makedirs(custom_sys_path, exist_ok=True)
    
    monkeypatch.setattr(sys, "path", ["", custom_sys_path, stdlib_path])

    finder = PathFinder(config, path=os.path.join(root_base, "root"))

    assert finder.virtual_env == os.path.realpath(venv_dir)
    assert finder.conda_env == os.path.realpath(conda_dir)
    assert os.path.normcase(site_packages) in [os.path.normcase(p) for p in finder.paths]
    assert os.path.normcase(nested_site_packages2) in [os.path.normcase(p) for p in finder.paths]
    assert os.path.normcase(valid_src_sub) in [os.path.normcase(p) for p in finder.paths]
    assert invalid_src_file not in finder.paths
    assert os.path.normcase(conda_site_packages) in [os.path.normcase(p) for p in finder.paths]
    assert os.path.normcase(conda_nested_site_packages) in [os.path.normcase(p) for p in finder.paths]
    assert stdlib_path in finder.paths
    assert custom_sys_path in finder.paths


def test_path_finder_env_vars(custom_tmp_dir, monkeypatch):
    root_base = os.path.realpath(custom_tmp_dir)
    venv_dir = os.path.join(root_base, "venv_env")
    conda_dir = os.path.join(root_base, "conda_env")
    os.makedirs(venv_dir, exist_ok=True)
    os.makedirs(conda_dir, exist_ok=True)

    monkeypatch.setenv("VIRTUAL_ENV", venv_dir)
    monkeypatch.setenv("CONDA_PREFIX", conda_dir)

    config = Config()  # No virtual_env or conda_env in config, should fall back to env vars
    finder = PathFinder(config, path=root_base)

    assert finder.virtual_env == os.path.realpath(venv_dir)
    assert finder.conda_env == os.path.realpath(conda_dir)


