# file: src\sample_repo\isort\isort\deprecated\finders.py:167-199
# asked: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 196, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 196], [195, 198]]}
# gained: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 196, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 196], [195, 198]]}

import importlib.machinery
import os
from pathlib import Path
import pytest

from isort import sections
from isort.deprecated.finders import PathFinder
from isort.settings import Config


def test_path_finder_find_branches(tmp_path):
    # Setup temporary directory structure to exercise PathFinder.find branches
    # 1. First party module / package inside src_paths
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    firstparty_pkg = src_dir / "my_firstparty_pkg"
    firstparty_pkg.mkdir()
    (firstparty_pkg / "__init__.py").write_text("")

    # 2. Third party module via site-packages prefix
    site_pkg_dir = tmp_path / "site-packages"
    site_pkg_dir.mkdir()
    (site_pkg_dir / "my_thirdparty.py").write_text("")

    # 3. Third party module via dist-packages prefix
    dist_pkg_dir = tmp_path / "dist-packages"
    dist_pkg_dir.mkdir()
    (dist_pkg_dir / "my_distparty.py").write_text("")

    # 4. Third party module via virtual_env / virtual_env_src
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    venv_src_dir = venv_dir / "src" / "my_venv_src_pkg"
    venv_src_dir.mkdir(parents=True)
    (venv_src_dir / "__init__.py").write_text("")

    # 5. Conda env module
    conda_dir = tmp_path / "conda"
    conda_dir.mkdir()
    (conda_dir / "my_conda_pkg.py").write_text("")

    # 6. Stdlib module (normcase(prefix) == stdlib_lib_prefix)
    stdlib_dir = tmp_path / "stdlib"
    stdlib_dir.mkdir()
    (stdlib_dir / "my_stdlib.py").write_text("")

    # 7. Default section module (random prefix)
    custom_dir = tmp_path / "custom"
    custom_dir.mkdir()
    (custom_dir / "my_custom.py").write_text("")

    # Configure Config
    config = Config(
        src_paths=[str(src_dir)],
        virtual_env=str(venv_dir),
        conda_env=str(conda_dir),
    )

    finder = PathFinder(config, path=str(tmp_path))
    # Override paths and stdlib prefix for deterministic testing of internal branches
    finder.paths = [
        str(site_pkg_dir),
        str(dist_pkg_dir),
        str(venv_src_dir.parent),  # contains virtual_env_src
        str(conda_dir),
        str(stdlib_dir),
        str(custom_dir),
        str(src_dir),
    ]
    finder.stdlib_lib_prefix = os.path.normcase(str(stdlib_dir))

    # Test site-packages -> THIRDPARTY
    assert finder.find("my_thirdparty") == sections.THIRDPARTY

    # Test dist-packages -> THIRDPARTY
    assert finder.find("my_distparty") == sections.THIRDPARTY

    # Test virtual_env_src -> THIRDPARTY
    assert finder.find("my_venv_src_pkg") == sections.THIRDPARTY

    # Test stdlib -> STDLIB
    assert finder.find("my_stdlib") == sections.STDLIB

    # Test conda_env -> THIRDPARTY
    assert finder.find("my_conda_pkg") == sections.THIRDPARTY

    # Test src_paths -> FIRSTPARTY
    assert finder.find("my_firstparty_pkg") == sections.FIRSTPARTY

    # Test default section -> default_section (e.g. THIRDPARTY or whatever config.default_section is)
    assert finder.find("my_custom") == config.default_section

    # Test module not found -> None
    assert finder.find("nonexistent_module_xyz") is None


def test_path_finder_find_stdlib_startswith(tmp_path):
    # Test line 195: normcase(prefix).startswith(stdlib_lib_prefix)
    stdlib_parent = tmp_path / "python"
    stdlib_parent.mkdir()
    sub_stdlib = stdlib_parent / "lib"
    sub_stdlib.mkdir()
    (sub_stdlib / "submod.py").write_text("")

    config = Config()
    finder = PathFinder(config, path=str(tmp_path))
    finder.paths = [str(sub_stdlib)]
    finder.stdlib_lib_prefix = os.path.normcase(str(stdlib_parent))

    assert finder.find("submod") == sections.STDLIB


def test_path_finder_extension_suffix(tmp_path):
    # Test finding a module with an extension suffix (line 173-174)
    ext_dir = tmp_path / "ext"
    ext_dir.mkdir()
    ext_suffix = importlib.machinery.EXTENSION_SUFFIXES[0]
    (ext_dir / f"my_ext{ext_suffix}").write_text("")

    config = Config()
    finder = PathFinder(config, path=str(tmp_path))
    finder.paths = [str(ext_dir)]

    assert finder.find("my_ext") == config.default_section
