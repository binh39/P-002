# file: src\sample_repo\isort\isort\deprecated\finders.py:121-165
# asked: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 136], [137, 138], [139, 140], [139, 142], [140, 139], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 150], [151, 152], [153, 154], [153, 158], [154, 153], [154, 155], [159, 160], [159, 163], [163, 0], [163, 164], [164, 163], [164, 165]]}
# gained: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 138], [139, 140], [139, 142], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 152], [153, 154], [153, 158], [154, 155], [159, 160], [163, 0], [163, 164], [164, 163], [164, 165]]}

import os
import sys
import sysconfig
from isort.deprecated.finders import PathFinder
from isort.settings import Config


def test_path_finder_init_full_branches(tmp_path):
    # Setup mock virtual environment structure
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    
    # 1. glob(f"{self.virtual_env}/lib/python*/site-packages")
    lib_path = venv_dir / "lib" / "python3.9" / "site-packages"
    lib_path.mkdir(parents=True)
    
    # 2. glob(f"{self.virtual_env}/lib/python*/*/site-packages")
    # python3.9/foo/site-packages
    nested_match = venv_dir / "lib" / "python3.9" / "foo" / "site-packages"
    nested_match.mkdir(parents=True)

    # 3. glob(f"{self.virtual_env}/src/*") + isdir
    src_sub = venv_dir / "src" / "pkg_src"
    src_sub.mkdir(parents=True)
    # Also create a non-dir file to test `if os.path.isdir(venv_src_path):` negative branch
    not_a_dir = venv_dir / "src" / "not_a_dir.txt"
    not_a_dir.write_text("hello")

    # Setup mock conda environment structure
    conda_dir = tmp_path / "conda"
    conda_dir.mkdir()
    conda_lib = conda_dir / "lib" / "python3.9" / "site-packages"
    conda_lib.mkdir(parents=True)
    conda_nested = conda_dir / "lib" / "python3.9" / "other" / "site-packages"
    conda_nested.mkdir(parents=True)

    # Configure Config with virtual_env and conda_env
    config = Config(
        virtual_env=str(venv_dir),
        conda_env=str(conda_dir),
    )

    # Temporarily ensure some paths are not yet in self.paths or already in self.paths to test `if path not in self.paths`
    old_sys_path = sys.path.copy()
    try:
        root_dir = os.path.abspath(tmp_path)
        sys.path.insert(1, root_dir)  # already in self.paths ([root_dir, src_dir])
        new_sys_path = str(tmp_path / "extra_sys_path")
        os.makedirs(new_sys_path, exist_ok=True)
        sys.path.insert(1, new_sys_path)

        finder = PathFinder(config, path=str(tmp_path))

        assert finder.virtual_env == os.path.realpath(venv_dir)
        assert finder.conda_env == os.path.realpath(conda_dir)
        
        # Normalize paths using os.path.normpath/os.path.realpath for robust path comparison across platforms
        resolved_paths = [os.path.realpath(p) for p in finder.paths]

        assert os.path.realpath(lib_path) in resolved_paths
        assert os.path.realpath(nested_match) in resolved_paths
        assert os.path.realpath(src_sub) in resolved_paths
        assert os.path.realpath(not_a_dir) not in resolved_paths
        assert os.path.realpath(conda_lib) in resolved_paths
        assert os.path.realpath(conda_nested) in resolved_paths
        assert os.path.realpath(new_sys_path) in resolved_paths

    finally:
        sys.path = old_sys_path


def test_path_finder_init_no_env(tmp_path):
    # Test when virtual_env and conda_env are empty/None, and stdlib / system paths are handled
    config = Config()
    
    old_venv = os.environ.pop("VIRTUAL_ENV", None)
    old_conda = os.environ.pop("CONDA_PREFIX", None)
    
    try:
        finder = PathFinder(config, path=str(tmp_path))
        assert not finder.virtual_env
        assert not finder.conda_env
        stdlib_path = os.path.normcase(sysconfig.get_paths()["stdlib"])
        assert stdlib_path in finder.paths
    finally:
        if old_venv is not None:
            os.environ["VIRTUAL_ENV"] = old_venv
        if old_conda is not None:
            os.environ["CONDA_PREFIX"] = old_conda
