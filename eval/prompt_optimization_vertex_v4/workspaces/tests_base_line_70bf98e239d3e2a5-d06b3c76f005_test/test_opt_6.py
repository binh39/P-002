# file: src\sample_repo\isort\isort\deprecated\finders.py:167-199
# asked: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 196, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 196], [195, 198]]}
# gained: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 198]]}

import importlib.machinery
import os
import sys
from pathlib import Path
import pytest

from isort import sections
from isort.deprecated.finders import PathFinder
from isort.settings import Config


def test_path_finder_find_branches(tmp_path):
    # Setup directories and files
    root = tmp_path / "root"
    root.mkdir()

    # 1. site-packages / dist-packages prefix -> THIRDPARTY
    sp_dir = root / "site-packages"
    sp_dir.mkdir()
    mod_sp = sp_dir / "mod_sp.py"
    mod_sp.write_text("# module")

    config = Config(settings_path=root)
    finder = PathFinder(config)
    finder.paths = [str(sp_dir)]
    assert finder.find("mod_sp") == sections.STDLIB or finder.find("mod_sp") == sections.THIRDPARTY
    # Specifically ensure site-packages branch is hit
    finder.paths = [str(sp_dir / "subdir-site-packages")]
    # Wait, let's explicitly build paths containing "site-packages" or "dist-packages"
    sp_path_str = str(root / "my_site_packages")
    os.makedirs(sp_path_str, exist_ok=True)
    mod_sp2 = Path(sp_path_str) / "mod_sp2.py"
    mod_sp2.write_text("")
    finder.paths = [sp_path_str]
    # "site-packages" or "dist-packages" in prefix -> THIRDPARTY
    # Let's use a path string containing "site-packages"
    sp_real_str = str(root / "site-packages" / "foo")
    os.makedirs(sp_real_str, exist_ok=True)
    Path(sp_real_str, "mod3.py").write_text("")
    finder.paths = [sp_real_str]
    assert finder.find("mod3") == sections.THIRDPARTY

    # dist-packages
    dist_real_str = str(root / "dist-packages" / "foo")
    os.makedirs(dist_real_str, exist_ok=True)
    Path(dist_real_str, "mod4.py").write_text("")
    finder.paths = [dist_real_str]
    assert finder.find("mod4") == sections.THIRDPARTY

    # virtual_env and virtual_env_src in prefix -> THIRDPARTY
    finder.virtual_env = str(root / "venv")
    finder.virtual_env_src = str(root / "venv" / "src")
    venv_src_prefix = str(root / "venv" / "src" / "my_pkg")
    os.makedirs(venv_src_prefix, exist_ok=True)
    Path(venv_src_prefix, "mod5.py").write_text("")
    finder.paths = [venv_src_prefix]
    assert finder.find("mod5") == sections.THIRDPARTY

    # os.path.normcase(prefix) == self.stdlib_lib_prefix -> STDLIB
    finder.virtual_env = None
    finder.conda_env = None
    finder.stdlib_lib_prefix = os.path.normcase(str(root / "stdlib"))
    os.makedirs(finder.stdlib_lib_prefix, exist_ok=True)
    Path(finder.stdlib_lib_prefix, "mod6.py").write_text("")
    finder.paths = [finder.stdlib_lib_prefix]
    assert finder.find("mod6") == sections.STDLIB

    # conda_env in prefix -> THIRDPARTY
    finder.conda_env = str(root / "conda")
    conda_prefix = str(root / "conda" / "envs" / "foo")
    os.makedirs(conda_prefix, exist_ok=True)
    Path(conda_prefix, "mod7.py").write_text("")
    finder.paths = [conda_prefix]
    assert finder.find("mod7") == sections.THIRDPARTY

    # src_path in path_obj.parents and not is_skipped -> FIRSTPARTY
    finder.conda_env = None
    src_root = root / "src_root"
    pkg_dir = src_root / "mypkg"
    pkg_dir.mkdir(parents=True)
    Path(pkg_dir, "mod8.py").write_text("")
    config = Config(src_paths=[src_root], settings_path=root)
    finder = PathFinder(config)
    finder.paths = [str(src_root)]
    assert finder.find("mypkg.mod8") == sections.FIRSTPARTY

    # default_section -> returns default section
    other_dir = root / "other"
    other_dir.mkdir()
    Path(other_dir, "mod9.py").write_text("")
    config = Config(default_section="CUSTOMSECTION", settings_path=root)
    finder = PathFinder(config)
    finder.paths = [str(other_dir)]
    assert finder.find("mod9") == "CUSTOMSECTION"

    # Module not found / None return
    finder.paths = [str(other_dir)]
    assert finder.find("nonexistent") is None

    # Extension suffix test (e.g. .so or .pyd or similar from EXTENSION_SUFFIXES)
    if importlib.machinery.EXTENSION_SUFFIXES:
        ext = importlib.machinery.EXTENSION_SUFFIXES[0]
        ext_mod = other_dir / f"extmod{ext}"
        ext_mod.write_text("")
        assert finder.find("extmod") == "CUSTOMSECTION"

    # Package test (__init__.py exists)
    pkg_sub = other_dir / "subpkg"
    pkg_sub.mkdir()
    (pkg_sub / "__init__.py").write_text("")
    assert finder.find("subpkg") == "CUSTOMSECTION"
