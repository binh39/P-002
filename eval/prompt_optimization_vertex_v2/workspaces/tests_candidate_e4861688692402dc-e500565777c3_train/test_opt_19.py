# file: src\sample_repo\isort\isort\deprecated\finders.py:167-199
# asked: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 196, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 196], [195, 198]]}
# gained: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 198]]}

import os
import tempfile
from pathlib import Path
from isort.deprecated.finders import PathFinder
from isort.settings import Config
from isort import sections


def test_path_finder_not_found():
    with tempfile.TemporaryDirectory() as tmp_dir:
        config = Config()
        finder = PathFinder(config, path=tmp_dir)
        assert finder.find("nonexistent_module_xyz_12345") is None


def test_path_finder_thirdparty_site_packages():
    with tempfile.TemporaryDirectory() as tmp_dir:
        site_pkg = Path(tmp_dir) / "site-packages"
        site_pkg.mkdir()
        mod_file = site_pkg / "my_thirdparty_mod.py"
        mod_file.write_text("# module")

        config = Config()
        finder = PathFinder(config, path=tmp_dir)
        finder.paths = [str(site_pkg)]

        assert finder.find("my_thirdparty_mod") == sections.THIRDPARTY


def test_path_finder_thirdparty_dist_packages():
    with tempfile.TemporaryDirectory() as tmp_dir:
        dist_pkg = Path(tmp_dir) / "dist-packages"
        dist_pkg.mkdir()
        mod_file = dist_pkg / "my_dist_mod.py"
        mod_file.write_text("# module")

        config = Config()
        finder = PathFinder(config, path=tmp_dir)
        finder.paths = [str(dist_pkg)]

        assert finder.find("my_dist_mod") == sections.THIRDPARTY


def test_path_finder_virtual_env():
    with tempfile.TemporaryDirectory() as tmp_dir:
        venv_dir = Path(tmp_dir) / "venv"
        venv_src = venv_dir / "src"
        custom_src = venv_src / "custom_pkg"
        custom_src.mkdir(parents=True)
        mod_file = custom_src / "my_venv_mod.py"
        mod_file.write_text("# module")

        config = Config()
        finder = PathFinder(config, path=tmp_dir)
        finder.virtual_env = str(venv_dir)
        finder.virtual_env_src = str(venv_src) + "/"
        finder.paths = [str(custom_src)]

        assert finder.find("my_venv_mod") == sections.THIRDPARTY


def test_path_finder_stdlib():
    with tempfile.TemporaryDirectory() as tmp_dir:
        config = Config()
        finder = PathFinder(config, path=tmp_dir)
        
        dummy_dir = Path(tmp_dir) / "stdlib_dummy"
        dummy_dir.mkdir()
        mod_file = dummy_dir / "os.py"
        mod_file.write_text("# stdlib mock")

        finder.paths = [str(dummy_dir)]
        finder.stdlib_lib_prefix = os.path.normcase(str(dummy_dir))

        assert finder.find("os") == sections.STDLIB


def test_path_finder_conda_env():
    with tempfile.TemporaryDirectory() as tmp_dir:
        conda_dir = Path(tmp_dir) / "conda"
        conda_dir.mkdir()
        mod_file = conda_dir / "conda_mod.py"
        mod_file.write_text("# conda mod")

        config = Config()
        finder = PathFinder(config, path=tmp_dir)
        finder.conda_env = str(conda_dir)
        finder.paths = [str(conda_dir)]

        assert finder.find("conda_mod") == sections.THIRDPARTY


def test_path_finder_firstparty():
    with tempfile.TemporaryDirectory() as tmp_dir:
        src_dir = Path(tmp_dir) / "src"
        sub_pkg = src_dir / "my_firstparty"
        sub_pkg.mkdir(parents=True)
        mod_file = sub_pkg / "__init__.py"
        mod_file.write_text("# package")

        config = Config(src_paths=[str(src_dir)])
        finder = PathFinder(config, path=tmp_dir)
        finder.paths = [str(src_dir)]

        assert finder.find("my_firstparty") == sections.FIRSTPARTY


def test_path_finder_default_section():
    with tempfile.TemporaryDirectory() as tmp_dir:
        other_dir = Path(tmp_dir) / "other"
        other_dir.mkdir()
        mod_file = other_dir / "local_mod.py"
        mod_file.write_text("# local")

        config = Config(default_section="DEFAULT_SECTION")
        finder = PathFinder(config, path=tmp_dir)
        finder.stdlib_lib_prefix = "nonexistent_stdlib_prefix_abc"
        finder.paths = [str(other_dir)]

        assert finder.find("local_mod") == "DEFAULT_SECTION"
