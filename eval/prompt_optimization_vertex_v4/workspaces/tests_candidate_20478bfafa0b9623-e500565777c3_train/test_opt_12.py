# file: src\sample_repo\isort\isort\deprecated\finders.py:167-199
# asked: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 196, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 196], [195, 198]]}
# gained: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 196, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 196], [195, 198]]}

from pathlib import Path
import os
import sysconfig
import importlib.machinery
import pytest

from isort.deprecated.finders import PathFinder
from isort.settings import Config
from isort import sections


def test_path_finder_not_found(tmp_path):
    config = Config()
    finder = PathFinder(config, path=str(tmp_path))
    # Module that does not exist in any prefix path
    assert finder.find("nonexistent_module_123456789") is None


def test_path_finder_thirdparty_site_packages(tmp_path):
    site_dir = tmp_path / "site-packages"
    site_dir.mkdir()
    mod_dir = site_dir / "foo"
    mod_dir.mkdir()
    (mod_dir / "__init__.py").write_text("")

    config = Config()
    finder = PathFinder(config, path=str(tmp_path))
    finder.paths = [str(site_dir)]
    
    assert finder.find("foo") == sections.THIRDPARTY


def test_path_finder_thirdparty_dist_packages(tmp_path):
    dist_dir = tmp_path / "dist-packages"
    dist_dir.mkdir()
    mod_py = dist_dir / "foo.py"
    mod_py.write_text("")

    config = Config()
    finder = PathFinder(config, path=str(tmp_path))
    finder.paths = [str(dist_dir)]
    
    assert finder.find("foo") == sections.THIRDPARTY


def test_path_finder_thirdparty_virtual_env_src(tmp_path):
    venv_dir = tmp_path / "venv"
    src_dir = venv_dir / "src" / "my_pkg"
    src_dir.mkdir(parents=True)
    (src_dir / "__init__.py").write_text("")

    config = Config()
    finder = PathFinder(config, path=str(tmp_path))
    finder.virtual_env = str(venv_dir)
    finder.virtual_env_src = str(venv_dir / "src") + "/"
    finder.paths = [str(src_dir.parent)]

    assert finder.find("my_pkg") == sections.THIRDPARTY


def test_path_finder_stdlib(tmp_path):
    stdlib_dir = tmp_path / "stdlib"
    stdlib_dir.mkdir()
    mod_dir = stdlib_dir / "os"
    mod_dir.mkdir()
    (mod_dir / "__init__.py").write_text("")

    config = Config()
    finder = PathFinder(config, path=str(tmp_path))
    finder.stdlib_lib_prefix = os.path.normcase(str(stdlib_dir))
    finder.paths = [str(stdlib_dir)]

    assert finder.find("os") == sections.STDLIB


def test_path_finder_conda_env(tmp_path):
    conda_dir = tmp_path / "conda"
    conda_dir.mkdir()
    mod_dir = conda_dir / "conda_mod"
    mod_dir.mkdir()
    (mod_dir / "__init__.py").write_text("")

    config = Config()
    finder = PathFinder(config, path=str(tmp_path))
    finder.conda_env = str(conda_dir)
    finder.paths = [str(conda_dir)]

    assert finder.find("conda_mod") == sections.THIRDPARTY


def test_path_finder_firstparty(tmp_path):
    src_root = tmp_path / "project"
    src_root.mkdir()
    pkg_dir = src_root / "my_first_party"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")

    config = Config(src_paths=[src_root])
    finder = PathFinder(config, path=str(tmp_path))
    finder.paths = [str(src_root)]

    assert finder.find("my_first_party") == sections.FIRSTPARTY


def test_path_finder_default_section(tmp_path):
    custom_dir = tmp_path / "custom"
    custom_dir.mkdir()
    mod_dir = custom_dir / "custom_mod"
    mod_dir.mkdir()
    (mod_dir / "__init__.py").write_text("")

    config = Config(default_section="CUSTOMSECTION")
    finder = PathFinder(config, path=str(tmp_path))
    finder.stdlib_lib_prefix = "nonexistent_stdlib_prefix_abc"
    finder.paths = [str(custom_dir)]

    assert finder.find("custom_mod") == "CUSTOMSECTION"


def test_path_finder_extension_suffix(tmp_path):
    custom_dir = tmp_path / "custom"
    custom_dir.mkdir()
    
    ext = importlib.machinery.EXTENSION_SUFFIXES[0]
    ext_file = custom_dir / f"ext_mod{ext}"
    ext_file.write_text("")

    config = Config(default_section="CUSTOMSECTION")
    finder = PathFinder(config, path=str(tmp_path))
    finder.stdlib_lib_prefix = "nonexistent_stdlib_prefix_abc"
    finder.paths = [str(custom_dir)]

    assert finder.find("ext_mod") == "CUSTOMSECTION"


def test_path_finder_stdlib_startswith(tmp_path):
    stdlib_parent = tmp_path / "lib"
    stdlib_parent.mkdir()
    stdlib_dir = stdlib_parent / "python3"
    stdlib_dir.mkdir()
    mod_dir = stdlib_dir / "math"
    mod_dir.mkdir()
    (mod_dir / "__init__.py").write_text("")

    config = Config()
    finder = PathFinder(config, path=str(tmp_path))
    # normcase(prefix) starts with stdlib_lib_prefix (e.g. parent vs child or prefix vs subpath)
    finder.stdlib_lib_prefix = os.path.normcase(str(stdlib_parent))
    finder.paths = [str(stdlib_dir)]

    assert finder.find("math") == sections.STDLIB
