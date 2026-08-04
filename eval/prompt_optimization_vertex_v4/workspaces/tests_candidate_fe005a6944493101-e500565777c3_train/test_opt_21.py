# file: src\sample_repo\isort\isort\deprecated\finders.py:167-199
# asked: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 196, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 196], [195, 198]]}
# gained: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 196, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 196], [195, 198]]}

import os
import sys
import tempfile
import importlib.machinery
from pathlib import Path

from isort import sections
from isort.settings import Config
from isort.deprecated.finders import PathFinder


def test_path_finder_find_coverage(tmp_path):
    # Setup temporary directory structure for testing various branches in PathFinder.find
    # 1. site-packages / dist-packages -> THIRDPARTY
    # 2. stdlib_lib_prefix -> STDLIB
    # 3. conda_env -> THIRDPARTY
    # 4. src_paths (first-party) -> FIRSTPARTY
    # 5. stdlib_lib_prefix startswith -> STDLIB
    # 6. default_section -> default_section (e.g. THIRDPARTY or similar)
    # 7. None when not found

    # Create a temporary project structure
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    
    src_dir = project_dir / "src"
    src_dir.mkdir()

    # Create dummy modules/packages in different paths
    
    # First party module under src_dir
    fp_mod_dir = src_dir / "my_first_party"
    fp_mod_dir.mkdir()
    (fp_mod_dir / "__init__.py").write_text("")

    # Config with src_paths
    config = Config(settings_path=project_dir, src_paths=[str(src_dir)])

    finder = PathFinder(config, path=str(project_dir))

    # Test 1: First party module
    # prefix will be str(src_dir) or project_dir, path_obj parents will contain src_path
    section = finder.find("my_first_party")
    assert section == sections.FIRSTPARTY

    # Test 2: site-packages or dist-packages in prefix -> THIRDPARTY
    sp_dir = tmp_path / "site-packages"
    sp_dir.mkdir()
    (sp_dir / "third_party_mod.py").write_text("")
    finder.paths = [str(sp_dir)]
    assert finder.find("third_party_mod") == sections.THIRDPARTY

    dp_dir = tmp_path / "dist-packages"
    dp_dir.mkdir()
    (dp_dir / "dist_party_mod.py").write_text("")
    finder.paths = [str(dp_dir)]
    assert finder.find("dist_party_mod") == sections.THIRDPARTY

    # Test 2b: virtual_env and virtual_env_src in prefix -> THIRDPARTY
    finder.virtual_env = str(tmp_path / "venv")
    finder.virtual_env_src = str(tmp_path / "venv" / "src")
    venv_src_mod = tmp_path / "venv" / "src" / "venv_mod"
    venv_src_mod.mkdir(parents=True)
    (venv_src_mod / "__init__.py").write_text("")
    finder.paths = [str(venv_src_mod.parent)]
    assert finder.find("venv_mod") == sections.THIRDPARTY

    # Test 3: os.path.normcase(prefix) == self.stdlib_lib_prefix -> STDLIB
    finder.virtual_env = None
    finder.conda_env = None
    std_dir = tmp_path / "stdlib"
    std_dir.mkdir()
    (std_dir / "os.py").write_text("")
    finder.stdlib_lib_prefix = os.path.normcase(str(std_dir))
    finder.paths = [str(std_dir)]
    assert finder.find("os") == sections.STDLIB

    # Test 4: conda_env and conda_env in prefix -> THIRDPARTY
    conda_dir = tmp_path / "conda"
    conda_dir.mkdir()
    (conda_dir / "conda_mod.py").write_text("")
    finder.stdlib_lib_prefix = "nonexistent_stdlib"
    finder.conda_env = str(conda_dir)
    finder.paths = [str(conda_dir)]
    assert finder.find("conda_mod") == sections.THIRDPARTY

    # Test 5: os.path.normcase(prefix).startswith(self.stdlib_lib_prefix) -> STDLIB
    finder.conda_env = None
    sub_std_dir = std_dir / "sub"
    sub_std_dir.mkdir()
    (sub_std_dir / "sub_std.py").write_text("")
    finder.stdlib_lib_prefix = os.path.normcase(str(std_dir))
    finder.paths = [str(sub_std_dir)]
    assert finder.find("sub_std") == sections.STDLIB

    # Test 6: default_section fallback (e.g. when prefix is a random path)
    random_dir = tmp_path / "random"
    random_dir.mkdir()
    (random_dir / "random_mod.py").write_text("")
    finder.stdlib_lib_prefix = "nonexistent_stdlib"
    finder.paths = [str(random_dir)]
    config_with_default = Config(settings_path=project_dir, default_section=sections.THIRDPARTY)
    finder.config = config_with_default
    assert finder.find("random_mod") == sections.THIRDPARTY

    # Test 7: Returns None when module not found in any path
    finder.paths = [str(random_dir)]
    assert finder.find("nonexistent_module_xyz") is None
