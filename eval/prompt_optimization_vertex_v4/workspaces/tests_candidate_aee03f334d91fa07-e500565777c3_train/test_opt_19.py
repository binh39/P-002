# file: src\sample_repo\isort\isort\deprecated\finders.py:167-199
# asked: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 196, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 196], [195, 198]]}
# gained: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 196, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 196], [195, 198]]}

from pathlib import Path
import sysconfig
import os
from isort.deprecated.finders import PathFinder
from isort.settings import Config
from isort import sections


def test_path_finder_find_all_branches(tmp_path):
    # Setup config and temporary directory structure
    d = tmp_path / "project"
    d.mkdir()
    
    # Create module in prefix directly
    mod_file = d / "mymod.py"
    mod_file.write_text("# module")

    # Create a package in site-packages prefix
    site_dir = d / "site-packages"
    site_dir.mkdir()
    site_pkg = site_dir / "sitepkg"
    site_pkg.mkdir()
    (site_pkg / "__init__.py").write_text("# pkg")

    # Create a package in dist-packages prefix
    dist_dir = d / "dist-packages"
    dist_dir.mkdir()
    dist_pkg = dist_dir / "distpkg"
    dist_pkg.mkdir()
    (dist_pkg / "__init__.py").write_text("# pkg")

    # Create virtualenv src prefix
    venv_dir = d / "venv"
    venv_dir.mkdir()
    venv_src = venv_dir / "src" / "venvsrcpkg"
    venv_src.mkdir(parents=True)
    (venv_src / "__init__.py").write_text("# venv src pkg")

    # Create stdlib prefix match
    stdlib_prefix = os.path.normcase(sysconfig.get_paths()["stdlib"])

    # Create conda prefix containing conda_env
    conda_dir = d / "conda_env"
    conda_dir.mkdir()
    conda_pkg = conda_dir / "condapkg"
    conda_pkg.mkdir()
    (conda_pkg / "__init__.py").write_text("# conda pkg")

    # Create first party src_paths match
    src_path = d / "src"
    src_path.mkdir()
    first_pkg = src_path / "firstpkg"
    first_pkg.mkdir()
    (first_pkg / "__init__.py").write_text("# first party pkg")

    # Create default section path (not site/dist/venv/stdlib/conda, and not in src_paths parents)
    other_dir = d / "other"
    other_dir.mkdir()
    other_mod = other_dir / "othermod.py"
    other_mod.write_text("# other")

    # Initialize PathFinder with custom paths and configs
    config = Config(src_paths=[str(src_path)])
    finder = PathFinder(config)
    
    # 1. site-packages -> THIRDPARTY
    finder.paths = [str(site_dir)]
    finder.virtual_env = None
    finder.conda_env = None
    assert finder.find("sitepkg") == sections.THIRDPARTY

    # 2. dist-packages -> THIRDPARTY
    finder.paths = [str(dist_dir)]
    assert finder.find("distpkg") == sections.THIRDPARTY

    # 3. virtual_env and virtual_env_src in prefix -> THIRDPARTY
    finder.paths = [str(venv_dir / "src")]
    finder.virtual_env = str(venv_dir)
    finder.virtual_env_src = str(venv_dir / "src") + "/"
    assert finder.find("venvsrcpkg") == sections.THIRDPARTY

    # 4. stdlib_lib_prefix == normcase(prefix) -> STDLIB
    custom_stdlib = d / "stdlib_custom"
    custom_stdlib.mkdir()
    (custom_stdlib / "stdmod.py").write_text("# std")
    finder.paths = [str(custom_stdlib)]
    finder.virtual_env = None
    finder.conda_env = None
    finder.stdlib_lib_prefix = os.path.normcase(str(custom_stdlib))
    assert finder.find("stdmod") == sections.STDLIB

    # 5. conda_env in prefix -> THIRDPARTY
    finder.paths = [str(conda_dir)]
    finder.conda_env = str(conda_dir)
    finder.stdlib_lib_prefix = "nonexistent_stdlib"
    assert finder.find("condapkg") == sections.THIRDPARTY

    # 6. src_path in path_obj.parents and not is_skipped -> FIRSTPARTY
    finder.paths = [str(src_path)]
    finder.conda_env = None
    assert finder.find("firstpkg") == sections.FIRSTPARTY

    # 7. normcase(prefix).startswith(stdlib_lib_prefix) -> STDLIB
    sub_stdlib = Path(stdlib_prefix) / "subdir"
    sub_stdlib.mkdir(exist_ok=True)
    (sub_stdlib / "submod.py").write_text("# submod")
    finder.paths = [str(sub_stdlib)]
    finder.stdlib_lib_prefix = os.path.normcase(stdlib_prefix)
    assert finder.find("submod") == sections.STDLIB

    # 8. default_section
    finder.paths = [str(other_dir)]
    finder.stdlib_lib_prefix = "nonexistent_stdlib"
    assert finder.find("othermod") == config.default_section

    # 9. Returns None when module not found in any path
    finder.paths = [str(other_dir)]
    assert finder.find("nonexistent") is None
