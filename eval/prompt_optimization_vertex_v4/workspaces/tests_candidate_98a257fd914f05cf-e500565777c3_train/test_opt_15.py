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


def test_path_finder_find_coverage(tmp_path):
    # Setup a dummy project structure
    site_pkg = tmp_path / "site-packages"
    site_pkg.mkdir()
    (site_pkg / "pkg_site.py").write_text("# module")

    dist_pkg = tmp_path / "dist-packages"
    dist_pkg.mkdir()
    (dist_pkg / "pkg_dist.py").write_text("# module")

    venv_dir = tmp_path / "venv"
    venv_src = venv_dir / "src" / "pkg_venv_src"
    venv_src.mkdir(parents=True)
    (venv_src / "__init__.py").write_text("# package")

    stdlib_dir = tmp_path / "stdlib"
    stdlib_dir.mkdir()
    (stdlib_dir / "pkg_stdlib.py").write_text("# module")

    conda_dir = tmp_path / "conda"
    conda_dir.mkdir()
    (conda_dir / "pkg_conda.py").write_text("# module")

    src_paths_root = tmp_path / "src_paths"
    first_dir = src_paths_root / "pkg_first"
    first_dir.mkdir(parents=True)
    (first_dir / "pkg_first.py").write_text("# module")

    default_dir = tmp_path / "default"
    default_dir.mkdir()
    (default_dir / "pkg_default.py").write_text("# module")

    # Extension suffix test case
    ext_dir = tmp_path / "ext"
    ext_dir.mkdir()
    ext_suffix = importlib.machinery.EXTENSION_SUFFIXES[0]
    (ext_dir / f"pkg_ext{ext_suffix}").write_text("# extension")

    config = Config(src_paths=[str(src_paths_root.resolve())])
    finder = PathFinder(config, path=str(tmp_path))

    # Manually tweak paths and properties to exercise all branches in lines 167-199
    finder.virtual_env = str(venv_dir)
    finder.virtual_env_src = str(venv_dir / "src") + "/"
    finder.stdlib_lib_prefix = os.path.normcase(str(stdlib_dir))
    finder.conda_env = str(conda_dir)

    # 1. Test site-packages -> THIRDPARTY (line 182-186)
    finder.paths = [str(site_pkg)]
    assert finder.find("pkg_site") == sections.THIRDPARTY

    # 2. Test dist-packages -> THIRDPARTY (line 183-186)
    finder.paths = [str(dist_pkg)]
    assert finder.find("pkg_dist") == sections.THIRDPARTY

    # 3. Test virtual_env and virtual_env_src in prefix -> THIRDPARTY (line 184, 186)
    finder.paths = [str(venv_src.parent)]
    assert finder.find("pkg_venv_src") == sections.THIRDPARTY

    # 4. Test stdlib -> STDLIB (line 187-188)
    finder.paths = [str(stdlib_dir)]
    assert finder.find("pkg_stdlib") == sections.STDLIB

    # 5. Test conda_env -> THIRDPARTY (line 189-190)
    finder.paths = [str(conda_dir)]
    assert finder.find("pkg_conda") == sections.THIRDPARTY

    # 6. Test src_paths -> FIRSTPARTY (line 191-193)
    finder.paths = [str(src_paths_root)]
    assert finder.find("pkg_first") == sections.FIRSTPARTY

    # 7. Test stdlib prefix startswith -> STDLIB (line 195-196)
    finder.paths = [str(stdlib_dir)]
    finder.stdlib_lib_prefix = os.path.normcase(str(tmp_path))
    assert finder.find("pkg_stdlib") == sections.STDLIB

    # 8. Test extension suffix match (line 173-174) + default section (line 198)
    finder.paths = [str(ext_dir)]
    finder.stdlib_lib_prefix = "nonexistent_stdlib"
    finder.conda_env = ""
    assert finder.find("pkg_ext") == config.default_section

    # 9. Test default section return (line 198)
    finder.paths = [str(default_dir)]
    assert finder.find("pkg_default") == config.default_section

    # 10. Test module not found -> None (line 199)
    finder.paths = [str(default_dir)]
    assert finder.find("nonexistent_module") is None
