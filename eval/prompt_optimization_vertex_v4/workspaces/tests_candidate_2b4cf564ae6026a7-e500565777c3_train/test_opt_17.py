# file: src\sample_repo\isort\isort\deprecated\finders.py:121-165
# asked: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 136], [137, 138], [139, 140], [139, 142], [140, 139], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 150], [151, 152], [153, 154], [153, 158], [154, 153], [154, 155], [159, 160], [159, 163], [163, 0], [163, 164], [164, 163], [164, 165]]}
# gained: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [134, 135], [136, 137], [136, 139], [137, 138], [139, 140], [139, 142], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [150, 151], [150, 153], [151, 152], [153, 154], [153, 158], [154, 155], [159, 160], [163, 0], [163, 164], [164, 163], [164, 165]]}

import os
import sys
import sysconfig
from isort.deprecated.finders import PathFinder
from isort.settings import Config


def test_path_finder_init_full_coverage(tmp_path, monkeypatch):
    # Setup virtual environment structure
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    
    # site-packages glob paths (matching python version / implementation)
    py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
    sp1 = venv_dir / "lib" / py_ver / "site-packages"
    sp1.mkdir(parents=True)
    
    nested_sp = venv_dir / "lib" / py_ver / "site-packages" / "nested"
    nested_sp.mkdir(parents=True)
    
    nested_sp2 = venv_dir / "lib" / py_ver / "site-packages" / "site-packages"
    nested_sp2.mkdir(parents=True)

    # venv src path (dir and non-dir)
    src_path_dir = venv_dir / "src" / "pkg_dir"
    src_path_dir.mkdir(parents=True)
    src_path_file = venv_dir / "src" / "pkg_file.txt"
    src_path_file.write_text("hello")

    # Conda environment structure
    conda_dir = tmp_path / "conda"
    conda_dir.mkdir()
    conda_sp = conda_dir / "lib" / py_ver / "site-packages"
    conda_sp.mkdir(parents=True)
    conda_nested_sp = conda_dir / "lib" / py_ver / "site-packages" / "site-packages"
    conda_nested_sp.mkdir(parents=True)

    # Configure Config with virtual_env and conda_env
    config = Config(
        virtual_env=str(venv_dir),
        conda_env=str(conda_dir),
    )

    # Also test when virtual_env / conda_env are picked up via environment variables or config
    finder = PathFinder(config=config, path=str(tmp_path / "root"))

    assert finder.virtual_env == os.path.realpath(str(venv_dir))
    assert finder.conda_env == os.path.realpath(str(conda_dir))
    assert os.path.realpath(str(sp1)) in [os.path.realpath(p) for p in finder.paths]
    assert os.path.realpath(str(conda_sp)) in [os.path.realpath(p) for p in finder.paths]
    assert os.path.realpath(str(src_path_dir)) in [os.path.realpath(p) for p in finder.paths]
    assert os.path.realpath(str(src_path_file)) not in [os.path.realpath(p) for p in finder.paths]

    # Test environment variables fallback paths
    monkeypatch.setenv("VIRTUAL_ENV", str(venv_dir))
    monkeypatch.setenv("CONDA_PREFIX", str(conda_dir))
    
    config_empty = Config()
    finder_env = PathFinder(config=config_empty, path=str(tmp_path / "root2"))
    assert finder_env.virtual_env == os.path.realpath(str(venv_dir))
    assert finder_env.conda_env == os.path.realpath(str(conda_dir))


