# file: src\sample_repo\isort\isort\deprecated\finders.py:167-199
# asked: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 196, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 196], [195, 198]]}
# gained: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 191, 192, 193, 199], "branches": [[168, 169], [168, 199], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 191], [191, 192], [192, 193]]}

from pathlib import Path
import os
import sys
import sysconfig
import pytest

from isort.deprecated.finders import PathFinder
from isort.settings import Config
from isort import sections


def test_path_finder_find_thirdparty_site_packages():
    # Tests line 182: "site-packages" in prefix -> THIRDPARTY
    # Avoid tmp_path fixture on Windows to prevent PermissionError when PathFinder instantiates
    # with sys.path entries that keep file handles or directory iterators open.
    base_dir = Path(os.getcwd()) / "_test_site_pkgs"
    pkg_dir = base_dir / "site-packages" / "foo"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "__init__.py").write_text("")
    try:
        config = Config()
        finder = PathFinder(config, path=str(base_dir))
        finder.paths = [str(base_dir / "site-packages")]
        assert finder.find("foo") == sections.THIRDPARTY
    finally:
        import shutil
        shutil.rmtree(base_dir, ignore_errors=True)


def test_path_finder_find_thirdparty_dist_packages():
    # Tests line 183: "dist-packages" in prefix -> THIRDPARTY
    base_dir = Path(os.getcwd()) / "_test_dist_pkgs"
    pkg_dir = base_dir / "dist-packages" / "foo"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "__init__.py").write_text("")
    try:
        config = Config()
        finder = PathFinder(config, path=str(base_dir))
        finder.paths = [str(base_dir / "dist-packages")]
        assert finder.find("foo") == sections.THIRDPARTY
    finally:
        import shutil
        shutil.rmtree(base_dir, ignore_errors=True)




def test_path_finder_find_stdlib():
    # Tests line 187: os.path.normcase(prefix) == self.stdlib_lib_prefix -> STDLIB
    base_dir = Path(os.getcwd()) / "_test_stdlib"
    foo_dir = base_dir / "foo"
    foo_dir.mkdir(parents=True, exist_ok=True)
    (foo_dir / "__init__.py").write_text("")
    try:
        config = Config()
        finder = PathFinder(config, path=str(base_dir))
        finder.stdlib_lib_prefix = os.path.normcase(str(base_dir))
        finder.paths = [str(base_dir)]
        assert finder.find("foo") == sections.STDLIB
    finally:
        import shutil
        shutil.rmtree(base_dir, ignore_errors=True)


def test_path_finder_find_conda_env():
    # Tests lines 189-190: self.conda_env and self.conda_env in prefix -> THIRDPARTY
    base_dir = Path(os.getcwd()) / "_test_conda"
    conda_dir = base_dir / "conda"
    conda_site = conda_dir / "lib" / "python3.10" / "site-packages" / "foo"
    conda_site.mkdir(parents=True, exist_ok=True)
    (conda_site / "__init__.py").write_text("")
    try:
        config = Config()
        finder = PathFinder(config, path=str(base_dir))
        finder.conda_env = str(conda_dir)
        finder.paths = [str(conda_site.parent)]
        assert finder.find("foo") == sections.THIRDPARTY
    finally:
        import shutil
        shutil.rmtree(base_dir, ignore_errors=True)


def test_path_finder_find_firstparty():
    # Tests lines 191-193: src_path in path_obj.parents and not self.config.is_skipped(path_obj) -> FIRSTPARTY
    base_dir = Path(os.getcwd()) / "_test_firstparty"
    src_path = base_dir / "src"
    foo_dir = src_path / "foo"
    foo_dir.mkdir(parents=True, exist_ok=True)
    (foo_dir / "__init__.py").write_text("")
    try:
        config = Config(src_paths=[str(src_path)])
        finder = PathFinder(config, path=str(base_dir))
        finder.paths = [str(src_path)]
        assert finder.find("foo") == sections.FIRSTPARTY
    finally:
        import shutil
        shutil.rmtree(base_dir, ignore_errors=True)




def test_path_finder_find_none():
    # Tests line 199: returns None when no paths match the module/package
    config = Config()
    finder = PathFinder(config)
    finder.paths = []
    assert finder.find("nonexistent") is None
