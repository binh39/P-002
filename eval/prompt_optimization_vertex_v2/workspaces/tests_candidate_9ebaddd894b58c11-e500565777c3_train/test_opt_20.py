# file: src\sample_repo\isort\isort\deprecated\finders.py:167-199
# asked: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 196, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 196], [195, 198]]}
# gained: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 196, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 196], [195, 198]]}

import os
import sys
import sysconfig
from pathlib import Path
import pytest

from isort import sections
from isort.deprecated.finders import PathFinder
from isort.settings import Config


def test_path_finder_find_thirdparty_site_dist_packages(monkeypatch):
    # Tests:
    # - "site-packages" in prefix
    # - "dist-packages" in prefix
    # - (self.virtual_env and self.virtual_env_src in prefix)
    
    # Use a dummy string path prefix instead of filesystem tmp_path to avoid Windows file locking/permission issues
    site_prefix = "/fake/path/site-packages"
    config = Config()
    finder = PathFinder(config, path="/fake/path")
    finder.paths = [site_prefix]
    
    monkeypatch.setattr("isort.deprecated.finders.exists_case_sensitive", lambda p: True)
    monkeypatch.setattr("os.path.isdir", lambda p: True)

    assert finder.find("foo") == sections.THIRDPARTY

    dist_prefix = "/fake/path/dist-packages"
    finder.paths = [dist_prefix]
    assert finder.find("bar") == sections.THIRDPARTY

    # Test virtual_env and virtual_env_src in prefix
    venv_prefix = "/fake/venv/src/my_pkg"
    finder_venv = PathFinder(Config(), path="/fake/path")
    finder_venv.virtual_env = "/fake/venv"
    finder_venv.virtual_env_src = "/fake/venv/src/"
    finder_venv.paths = [venv_prefix]

    assert finder_venv.find("baz") == sections.THIRDPARTY


def test_path_finder_find_stdlib(monkeypatch):
    # Tests:
    # - os.path.normcase(prefix) == self.stdlib_lib_prefix
    stdlib_prefix = "/fake/stdlib"
    config = Config()
    finder = PathFinder(config, path="/fake/path")
    finder.stdlib_lib_prefix = os.path.normcase(stdlib_prefix)
    finder.paths = [stdlib_prefix]

    monkeypatch.setattr("isort.deprecated.finders.exists_case_sensitive", lambda p: True)
    monkeypatch.setattr("os.path.isdir", lambda p: True)

    assert finder.find("isort_test_dummy_mod") == sections.STDLIB


def test_path_finder_find_conda_env(monkeypatch):
    # Tests:
    # - self.conda_env and self.conda_env in prefix
    conda_prefix = "/fake/conda_env"
    config = Config()
    finder = PathFinder(config, path="/fake/path")
    finder.conda_env = conda_prefix
    finder.paths = [conda_prefix]

    monkeypatch.setattr("isort.deprecated.finders.exists_case_sensitive", lambda p: True)
    monkeypatch.setattr("os.path.isdir", lambda p: True)

    assert finder.find("qux") == sections.THIRDPARTY


def test_path_finder_find_first_party(monkeypatch):
    # Tests:
    # - src_path in path_obj.parents and not self.config.is_skipped(path_obj)
    src_dir = "/fake/path/src"
    pkg_prefix = "/fake/path/src/pkg"
    
    config = Config(src_paths=[src_dir])
    finder = PathFinder(config, path="/fake/path")
    finder.paths = [pkg_prefix]

    monkeypatch.setattr("isort.deprecated.finders.exists_case_sensitive", lambda p: True)
    monkeypatch.setattr("os.path.isdir", lambda p: True)

    assert finder.find("pkg.module") == sections.FIRSTPARTY


def test_path_finder_find_stdlib_normcase_startswith(monkeypatch):
    # Tests:
    # - os.path.normcase(prefix).startswith(self.stdlib_lib_prefix)
    stdlib_base = "/fake/stdlib"
    stdlib_sub = "/fake/stdlib/sub_folder"

    config = Config()
    finder = PathFinder(config, path="/fake/path")
    finder.stdlib_lib_prefix = os.path.normcase(stdlib_base)
    finder.paths = [stdlib_sub]

    monkeypatch.setattr("isort.deprecated.finders.exists_case_sensitive", lambda p: True)
    monkeypatch.setattr("os.path.isdir", lambda p: True)

    assert finder.find("isort_test_sub_mod") == sections.STDLIB


def test_path_finder_find_default_section_and_none(monkeypatch):
    # Tests:
    # - return self.config.default_section
    # - return None (when loop finishes without finding module/package)
    custom_prefix = "/fake/custom"

    config = Config(default_section="CUSTOMSECTION")
    finder = PathFinder(config, path="/fake/path")
    finder.paths = [custom_prefix]

    monkeypatch.setattr("isort.deprecated.finders.exists_case_sensitive", lambda p: True)
    monkeypatch.setattr("os.path.isdir", lambda p: True)

    assert finder.find("custom_mod") == "CUSTOMSECTION"

    # Test returning None when module is not found anywhere
    monkeypatch.setattr("isort.deprecated.finders.exists_case_sensitive", lambda p: False)
    monkeypatch.setattr("os.path.isdir", lambda p: False)
    assert finder.find("nonexistent_module_xyz") is None
