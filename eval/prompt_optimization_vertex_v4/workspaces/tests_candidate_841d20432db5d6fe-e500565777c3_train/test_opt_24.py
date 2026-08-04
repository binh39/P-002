# file: src\sample_repo\isort\isort\deprecated\finders.py:167-199
# asked: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 196, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 196], [195, 198]]}
# gained: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 196, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 196], [195, 198]]}

import importlib.machinery
import os
from pathlib import Path
from isort import sections
from isort.deprecated.finders import PathFinder
from isort.settings import Config


def test_path_finder_find_all_branches(tmp_path):
    # Setup temporary directory structure to test PathFinder.find branches
    # 1. Thirdparty via site-packages
    site_pkgs = tmp_path / "site-packages"
    site_pkgs.mkdir()
    mod_sp = site_pkgs / "mod_sp.py"
    mod_sp.write_text("x = 1")

    # 2. Stdlib via stdlib_lib_prefix
    stdlib_dir = tmp_path / "stdlib"
    stdlib_dir.mkdir()
    mod_std = stdlib_dir / "mod_std.py"
    mod_std.write_text("x = 1")

    # 3. Thirdparty via conda_env
    conda_dir = tmp_path / "conda"
    conda_dir.mkdir()
    mod_conda = conda_dir / "mod_conda.py"
    mod_conda.write_text("x = 1")

    # 4. Firstparty via src_paths (use a parent structure where src_path is in path_obj.parents)
    # path_obj = Path(package_path).resolve() where package_path = prefix + "/" + module_name
    # If prefix = tmp_path / "custom_prefix", package_path = prefix / "mod_first"
    # Then path_obj = prefix / "mod_first". For src_path to be in path_obj.parents,
    # src_path must be a parent of path_obj, e.g., src_path = str(tmp_path) or src_path = str(prefix)
    # But wait, config.src_paths usually contains paths. Let's make src_dir a parent of package_path.
    proj_dir = tmp_path / "proj"
    proj_dir.mkdir()
    src_dir = proj_dir / "src"
    src_dir.mkdir()
    mod_first = src_dir / "mod_first.py"
    mod_first.write_text("x = 1")

    # 5. Default section fallback
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    mod_other = other_dir / "mod_other.py"
    mod_other.write_text("x = 1")

    # Configure Config with absolute path for src_paths
    config = Config(src_paths=[str(proj_dir.resolve())])

    # Instantiate PathFinder and override its attributes to test each condition deterministically
    finder = PathFinder(config, path=str(tmp_path))

    # Test site-packages prefix -> THIRDPARTY
    finder.paths = [str(site_pkgs)]
    assert finder.find("mod_sp") == sections.THIRDPARTY

    # Test virtual_env and virtual_env_src prefix -> THIRDPARTY
    venv_dir = tmp_path / "venv"
    venv_src_dir = venv_dir / "src" / "my_pkg"
    venv_src_dir.mkdir(parents=True)
    mod_venv = venv_src_dir / "mod_venv.py"
    mod_venv.write_text("x = 1")
    finder.paths = [str(venv_src_dir)]
    finder.virtual_env = str(venv_dir)
    finder.virtual_env_src = str(venv_dir / "src") + "/"
    assert finder.find("mod_venv") == sections.THIRDPARTY

    # Test stdlib_lib_prefix exact match -> STDLIB
    finder.paths = [str(stdlib_dir)]
    finder.stdlib_lib_prefix = os.path.normcase(str(stdlib_dir.resolve()))
    assert finder.find("mod_std") == sections.STDLIB

    # Test conda_env match -> THIRDPARTY
    finder.paths = [str(conda_dir)]
    finder.conda_env = str(conda_dir)
    assert finder.find("mod_conda") == sections.THIRDPARTY

    # Test config.src_paths match -> FIRSTPARTY
    # prefix = str(proj_dir), module_name = "src.mod_first" or prefix = str(src_dir) and src_paths = [str(proj_dir.resolve())]
    # Let's set finder.paths = [str(proj_dir)] and find "src.mod_first"
    finder.paths = [str(proj_dir.resolve())]
    finder.virtual_env = None
    finder.conda_env = None
    finder.stdlib_lib_prefix = "/nonexistent/stdlib"
    assert finder.find("src") == sections.FIRSTPARTY

    # Test stdlib_lib_prefix startswith match (simulated via prefix starting with stdlib prefix)
    sub_stdlib = stdlib_dir / "sub"
    sub_stdlib.mkdir()
    mod_sub = sub_stdlib / "mod_sub.py"
    mod_sub.write_text("x = 1")
    finder.paths = [str(sub_stdlib.resolve())]
    finder.stdlib_lib_prefix = os.path.normcase(str(stdlib_dir.resolve()))
    assert finder.find("mod_sub") == sections.STDLIB

    # Test default section fallback
    finder.paths = [str(other_dir.resolve())]
    finder.stdlib_lib_prefix = "/nonexistent/stdlib"
    assert finder.find("mod_other") == config.default_section

    # Test return None when module not found in paths
    finder.paths = [str(other_dir.resolve())]
    assert finder.find("nonexistent_module") is None
