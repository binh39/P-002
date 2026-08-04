# file: src\sample_repo\isort\isort\deprecated\finders.py:167-199
# asked: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 196, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 196], [195, 198]]}
# gained: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 198]]}

import importlib.machinery
import os
from pathlib import Path
import pytest

from isort import sections
from isort.deprecated.finders import PathFinder
from isort.settings import Config


def test_path_finder_find_none():
    config = Config()
    finder = PathFinder(config, path=os.getcwd())
    assert finder.find("nonexistent_module_123456789") is None


def test_path_finder_thirdparty_site_packages():
    # Use standard library path which contains site-packages or just mock paths directly
    config = Config()
    finder = PathFinder(config)
    # We can test line 186 by injecting a path containing site-packages
    # and creating a dummy file matching it.
    # Instead of tmp_path, use a custom directory path or mock paths.
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        site_dir = os.path.join(tmpdir, "site-packages")
        os.makedirs(site_dir)
        mod_file = os.path.join(site_dir, "my_thirdparty_mod.py")
        with open(mod_file, "w") as f:
            f.write("# module")
        finder.paths = [site_dir]
        try:
            assert finder.find("my_thirdparty_mod") == sections.THIRDPARTY
        finally:
            if os.path.exists(mod_file):
                os.remove(mod_file)


def test_path_finder_thirdparty_dist_packages():
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        dist_dir = os.path.join(tmpdir, "dist-packages")
        os.makedirs(dist_dir)
        mod_file = os.path.join(dist_dir, "my_dist_mod.py")
        with open(mod_file, "w") as f:
            f.write("# module")
        config = Config()
        finder = PathFinder(config)
        finder.paths = [dist_dir]
        try:
            assert finder.find("my_dist_mod") == sections.THIRDPARTY
        finally:
            if os.path.exists(mod_file):
                os.remove(mod_file)


def test_path_finder_thirdparty_virtual_env():
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        venv_dir = os.path.join(tmpdir, "my_venv")
        venv_src = os.path.join(venv_dir, "src")
        mod_dir = os.path.join(venv_src, "my_venv_pkg")
        os.makedirs(mod_dir)
        init_file = os.path.join(mod_dir, "__init__.py")
        with open(init_file, "w") as f:
            f.write("# pkg")

        config = Config()
        finder = PathFinder(config)
        finder.virtual_env = venv_dir
        finder.virtual_env_src = venv_src + "/"
        finder.paths = [venv_src]
        try:
            assert finder.find("my_venv_pkg") == sections.THIRDPARTY
        finally:
            if os.path.exists(init_file):
                os.remove(init_file)


def test_path_finder_stdlib():
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        stdlib_dir = os.path.join(tmpdir, "stdlib_lib")
        os.makedirs(stdlib_dir)
        mod_file = os.path.join(stdlib_dir, "os.py")
        with open(mod_file, "w") as f:
            f.write("# stdlib")

        config = Config()
        finder = PathFinder(config)
        finder.stdlib_lib_prefix = os.path.normcase(stdlib_dir)
        finder.paths = [stdlib_dir]
        try:
            assert finder.find("os") == sections.STDLIB
        finally:
            if os.path.exists(mod_file):
                os.remove(mod_file)


def test_path_finder_conda_env():
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        conda_dir = os.path.join(tmpdir, "conda_prefix")
        os.makedirs(conda_dir)
        mod_file = os.path.join(conda_dir, "conda_mod.py")
        with open(mod_file, "w") as f:
            f.write("# conda")

        config = Config()
        finder = PathFinder(config)
        finder.conda_env = conda_dir
        finder.paths = [conda_dir]
        try:
            assert finder.find("conda_mod") == sections.THIRDPARTY
        finally:
            if os.path.exists(mod_file):
                os.remove(mod_file)


def test_path_finder_first_party():
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = os.path.join(tmpdir, "src")
        mod_dir = os.path.join(src_dir, "my_first_party")
        os.makedirs(mod_dir)
        init_file = os.path.join(mod_dir, "__init__.py")
        with open(init_file, "w") as f:
            f.write("# first party")

        config = Config(src_paths=[src_dir])
        finder = PathFinder(config)
        finder.paths = [src_dir]
        try:
            assert finder.find("my_first_party") == sections.FIRSTPARTY
        finally:
            if os.path.exists(init_file):
                os.remove(init_file)




def test_path_finder_default_section():
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        other_dir = os.path.join(tmpdir, "other")
        os.makedirs(other_dir)
        mod_file = os.path.join(other_dir, "custom_mod.py")
        with open(mod_file, "w") as f:
            f.write("# custom")

        config = Config(default_section="CUSTOMSECTION")
        finder = PathFinder(config)
        finder.stdlib_lib_prefix = os.path.normcase(os.path.join(tmpdir, "nonexistent"))
        finder.paths = [other_dir]
        try:
            assert finder.find("custom_mod") == "CUSTOMSECTION"
        finally:
            if os.path.exists(mod_file):
                os.remove(mod_file)


def test_path_finder_extension_suffix():
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        ext_dir = os.path.join(tmpdir, "ext")
        os.makedirs(ext_dir)
        suffix = importlib.machinery.EXTENSION_SUFFIXES[0]
        mod_file = os.path.join(ext_dir, f"c_ext_mod{suffix}")
        with open(mod_file, "w") as f:
            f.write("# binary ext")

        config = Config()
        finder = PathFinder(config)
        finder.stdlib_lib_prefix = os.path.normcase(os.path.join(tmpdir, "nonexistent"))
        finder.paths = [ext_dir]
        try:
            assert finder.find("c_ext_mod") == config.default_section
        finally:
            if os.path.exists(mod_file):
                os.remove(mod_file)
