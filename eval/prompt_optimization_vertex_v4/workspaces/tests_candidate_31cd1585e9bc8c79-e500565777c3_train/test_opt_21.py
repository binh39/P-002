# file: src\sample_repo\isort\isort\deprecated\finders.py:167-199
# asked: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 196, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 196], [195, 198]]}
# gained: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 198]]}

from pathlib import Path
import os
import sys
import sysconfig
from isort.deprecated.finders import PathFinder
from isort.settings import Config
from isort import sections


def test_path_finder_find_thirdparty_site_packages(tmp_path):
    # Tests:
    # - is_module or is_package (creates a directory or .py file)
    # - "site-packages" in prefix -> THIRDPARTY
    site_pkg = tmp_path / "site-packages"
    site_pkg.mkdir()
    mod_file = site_pkg / "my_module.py"
    mod_file.write_text("x = 1")

    config = Config()
    finder = PathFinder(config, path=str(tmp_path))
    # Override paths to include our site-packages directory
    finder.paths = [str(site_pkg)]

    result = finder.find("my_module")
    assert result == sections.THIRDPARTY


def test_path_finder_find_thirdparty_dist_packages(tmp_path):
    # Tests "dist-packages" in prefix -> THIRDPARTY
    dist_pkg = tmp_path / "dist-packages"
    dist_pkg.mkdir()
    mod_file = dist_pkg / "my_module.py"
    mod_file.write_text("x = 1")

    config = Config()
    finder = PathFinder(config, path=str(tmp_path))
    finder.paths = [str(dist_pkg)]

    result = finder.find("my_module")
    assert result == sections.THIRDPARTY


def test_path_finder_find_thirdparty_virtual_env_src(tmp_path):
    # Tests virtual_env and virtual_env_src in prefix -> THIRDPARTY
    venv = tmp_path / "venv"
    venv.mkdir()
    src_dir = venv / "src" / "mysub"
    src_dir.mkdir(parents=True)
    mod_file = src_dir / "my_module.py"
    mod_file.write_text("x = 1")

    config = Config()
    finder = PathFinder(config, path=str(tmp_path))
    finder.virtual_env = str(venv)
    finder.virtual_env_src = str(venv / "src") + "/"
    finder.paths = [str(src_dir)]

    result = finder.find("my_module")
    assert result == sections.THIRDPARTY


def test_path_finder_find_stdlib(tmp_path):
    # Tests os.path.normcase(prefix) == self.stdlib_lib_prefix -> STDLIB
    stdlib_path = sysconfig.get_paths()["stdlib"]
    stdlib_dir = Path(stdlib_path)
    if not stdlib_dir.exists():
        stdlib_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a dummy stdlib module file inside stdlib_dir
    mod_file = stdlib_dir / "test_stdlib_mod.py"
    mod_file.write_text("x = 1")
    try:
        config = Config()
        finder = PathFinder(config, path=str(tmp_path))
        finder.paths = [str(stdlib_dir)]

        result = finder.find("test_stdlib_mod")
        assert result == sections.STDLIB
    finally:
        if mod_file.exists():
            mod_file.unlink()


def test_path_finder_find_conda_env(tmp_path):
    # Tests self.conda_env and self.conda_env in prefix -> THIRDPARTY
    conda_dir = tmp_path / "conda"
    conda_dir.mkdir()
    mod_file = conda_dir / "my_module.py"
    mod_file.write_text("x = 1")

    config = Config()
    finder = PathFinder(config, path=str(tmp_path))
    finder.conda_env = str(conda_dir)
    finder.paths = [str(conda_dir)]

    result = finder.find("my_module")
    assert result == sections.THIRDPARTY


def test_path_finder_find_firstparty(tmp_path):
    # Tests src_path in path_obj.parents and not self.config.is_skipped(path_obj) -> FIRSTPARTY
    src_dir = tmp_path / "src"
    pkg_dir = src_dir / "my_pkg"
    pkg_dir.mkdir(parents=True)
    mod_file = pkg_dir / "__init__.py"
    mod_file.write_text("x = 1")

    config = Config(src_paths=[src_dir.resolve()])
    finder = PathFinder(config, path=str(tmp_path))
    finder.paths = [str(src_dir.resolve())]

    result = finder.find("my_pkg")
    assert result == sections.FIRSTPARTY


def test_path_finder_find_default_section(tmp_path):
    # Tests falling back to self.config.default_section
    custom_dir = tmp_path / "custom"
    custom_dir.mkdir()
    mod_file = custom_dir / "my_module.py"
    mod_file.write_text("x = 1")

    config = Config(default_section="CUSTOM_SECTION")
    finder = PathFinder(config, path=str(tmp_path))
    finder.paths = [str(custom_dir)]

    result = finder.find("my_module")
    assert result == "CUSTOM_SECTION"


def test_path_finder_find_none(tmp_path):
    # Tests returning None when module is not found
    config = Config()
    finder = PathFinder(config, path=str(tmp_path))
    # Make sure paths only contains empty or non-existent things
    finder.paths = [str(tmp_path / "nonexistent")]

    result = finder.find("nonexistent_module")
    assert result is None
