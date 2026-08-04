# file: src\sample_repo\isort\isort\deprecated\finders.py:167-199
# asked: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 196, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 196], [195, 198]]}
# gained: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 198]]}

from pathlib import Path
import importlib.machinery
from isort import sections
from isort.deprecated.finders import PathFinder
from isort.settings import Config


def test_path_finder_find_branches(tmp_path):
    # Setup directories and files
    root = tmp_path / "project"
    root.mkdir()
    
    # 1. THIRDPARTY via site-packages in prefix
    site_pkg = root / "site-packages"
    site_pkg.mkdir()
    mod_file = site_pkg / "my_module.py"
    mod_file.write_text("print('hello')")

    config = Config(settings_path=root)
    finder = PathFinder(config, path=str(root))
    finder.paths = [str(site_pkg)]
    assert finder.find("my_module") == sections.THIRDPARTY

    # 2. THIRDPARTY via dist-packages in prefix
    dist_pkg = root / "dist-packages"
    dist_pkg.mkdir()
    (dist_pkg / "dist_module.py").write_text("x = 1")
    finder.paths = [str(dist_pkg)]
    assert finder.find("dist_module") == sections.THIRDPARTY

    # 3. THIRDPARTY via virtual_env and virtual_env_src
    venv = root / "venv"
    venv.mkdir()
    venv_src = venv / "src"
    venv_src.mkdir()
    sub_src = venv_src / "subpkg"
    sub_src.mkdir()
    (sub_src / "venv_mod.py").write_text("x = 1")

    finder.virtual_env = str(venv)
    finder.virtual_env_src = str(venv_src) + "/"
    finder.paths = [str(sub_src)]
    assert finder.find("venv_mod") == sections.THIRDPARTY

    # 4. STDLIB via os.path.normcase(prefix) == self.stdlib_lib_prefix
    finder.paths = [finder.stdlib_lib_prefix]
    # Create a dummy module or package in stdlib prefix
    stdlib_mod = Path(finder.stdlib_lib_prefix) / "os.py"
    # We don't necessarily want to mess with real stdlib, but we can mock or use a temp dir as stdlib_lib_prefix
    custom_stdlib = root / "stdlib"
    custom_stdlib.mkdir()
    (custom_stdlib / "std_mod.py").write_text("pass")
    finder.stdlib_lib_prefix = os_normcase = os.path.normcase(str(custom_stdlib))
    finder.paths = [str(custom_stdlib)]
    assert finder.find("std_mod") == sections.STDLIB

    # 5. THIRDPARTY via conda_env and conda_env in prefix
    conda = root / "conda"
    conda.mkdir()
    (conda / "conda_mod.py").write_text("pass")
    finder.conda_env = str(conda)
    finder.paths = [str(conda)]
    assert finder.find("conda_mod") == sections.THIRDPARTY

    # 6. FIRSTPARTY via src_path in path_obj.parents and not skipped
    src_dir = root / "src"
    src_dir.mkdir()
    pkg_dir = src_dir / "my_firstparty"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")

    config = Config(src_paths=[str(src_dir)], settings_path=root)
    finder = PathFinder(config, path=str(root))
    finder.paths = [str(src_dir)]
    assert finder.find("my_firstparty") == sections.FIRSTPARTY

    # 7. DEFAULT_SECTION when none of the above match, but module exists
    other_dir = root / "other"
    other_dir.mkdir()
    (other_dir / "other_mod.py").write_text("")
    config = Config(default_section="CUSTOM_SECTION", settings_path=root)
    finder = PathFinder(config, path=str(root))
    finder.paths = [str(other_dir)]
    assert finder.find("other_mod") == "CUSTOM_SECTION"

    # 8. Returns None when module is not found anywhere
    finder.paths = [str(other_dir)]
    assert finder.find("nonexistent_module") is None


import os
