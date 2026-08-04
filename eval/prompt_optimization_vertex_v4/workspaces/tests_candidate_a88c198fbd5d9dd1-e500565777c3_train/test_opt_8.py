# file: src\sample_repo\isort\isort\deprecated\finders.py:121-165
# asked: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 136], [137, 138], [139, 140], [139, 142], [140, 139], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 150], [151, 152], [153, 154], [153, 158], [154, 153], [154, 155], [159, 160], [159, 163], [163, 0], [163, 164], [164, 163], [164, 165]]}
# gained: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 138], [139, 140], [139, 142], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 152], [153, 154], [153, 158], [154, 155], [159, 160], [163, 0], [163, 164], [164, 163], [164, 165]]}

import os
import sys
import sysconfig
from isort.deprecated.finders import PathFinder
from isort.settings import Config


def test_path_finder_init_full_coverage(tmp_path, monkeypatch):
    # Setup virtual environment structure
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    
    # site-packages paths using os.path.join / path formatting matching glob
    # glob uses forward slashes or whatever glob returns. Let's normalize paths or use os.path.normpath / os.path.realpath.
    site_packages = venv_dir / "lib" / "python3.10" / "site-packages"
    site_packages.mkdir(parents=True)
    
    # glob pattern is f"{self.virtual_env}/lib/python*/*/site-packages"
    # On Windows, glob(f"{self.virtual_env}/lib/python*/*/site-packages") returns backslashes or forward slashes depending on glob implementation,
    # but the paths appended are whatever glob() finds (or we can check os.path.realpath or os.path.normcase).
    nested_match = venv_dir / "lib" / "python3.10" / "site-packages" / "site-packages"
    nested_match.mkdir(parents=True, exist_ok=True)

    # 3. {venv}/src/* (must be dir)
    venv_src_sub = venv_dir / "src" / "pkg"
    venv_src_sub.mkdir(parents=True)
    # also a non-dir file in venv/src/ to test os.path.isdir branch
    not_a_dir = venv_dir / "src" / "not_a_dir.txt"
    not_a_dir.write_text("hello")

    # Conda environment structure
    conda_dir = tmp_path / "conda"
    conda_dir.mkdir()
    conda_site_packages = conda_dir / "lib" / "python3.10" / "site-packages"
    conda_site_packages.mkdir(parents=True)
    conda_nested = conda_dir / "lib" / "python3.10" / "site-packages" / "site-packages"
    conda_nested.mkdir(parents=True, exist_ok=True)

    # Configure Config with virtual_env and conda_env
    config = Config(virtual_env=str(venv_dir), conda_env=str(conda_dir))

    # Also test when stdlib_lib_prefix is already in self.paths or not
    old_sys_path = sys.path[:]
    extra_path = str(tmp_path / "extra_sys_path")
    sys.path.append(extra_path)

    try:
        finder = PathFinder(config, path=str(tmp_path / "root"))
        assert finder.virtual_env == os.path.realpath(str(venv_dir))
        assert finder.conda_env == os.path.realpath(str(conda_dir))

        # Check path existence using os.path.realpath normalization to handle slash differences across platforms
        finder_paths_real = {os.path.realpath(p) for p in finder.paths}

        assert os.path.realpath(str(site_packages)) in finder_paths_real
        assert os.path.realpath(str(nested_match)) in finder_paths_real
        assert os.path.realpath(str(venv_src_sub)) in finder_paths_real
        assert os.path.realpath(str(not_a_dir)) not in finder_paths_real
        assert os.path.realpath(str(conda_site_packages)) in finder_paths_real
        assert os.path.realpath(str(conda_nested)) in finder_paths_real
        assert os.path.realpath(finder.stdlib_lib_prefix) in finder_paths_real
        assert os.path.realpath(extra_path) in finder_paths_real
    finally:
        sys.path[:] = old_sys_path


def test_path_finder_init_env_fallback(tmp_path, monkeypatch):
    # Test fallback to os.environ and empty values / defaults
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.delenv("CONDA_PREFIX", raising=False)

    config = Config()
    finder = PathFinder(config, path=str(tmp_path))
    assert finder.virtual_env is None
    assert finder.conda_env == ""
