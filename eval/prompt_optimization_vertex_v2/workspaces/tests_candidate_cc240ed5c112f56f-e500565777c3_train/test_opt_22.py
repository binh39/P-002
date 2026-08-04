# file: src\sample_repo\isort\isort\deprecated\finders.py:167-199
# asked: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 196, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 196], [195, 198]]}
# gained: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 187, 189, 191, 192, 195, 198], "branches": [[168, 169], [180, 181], [181, 187], [187, 189], [189, 191], [191, 192], [191, 195], [192, 191], [195, 198]]}

import os
import sys
import sysconfig
import importlib.machinery
from pathlib import Path
from isort import sections
from isort.settings import Config
from isort.deprecated.finders import PathFinder




def test_path_finder_extension_and_package_variants():
    import tempfile
    tmp_dir = tempfile.TemporaryDirectory()
    tmp_path = Path(tmp_dir.name)
    try:
        # Test extension suffixes and package variants (is_module with extension, __init__.py, is_package)
        mod_dir = tmp_path / "mod_test"
        mod_dir.mkdir()
        
        # 1. Extension suffix match
        ext_suffix = importlib.machinery.EXTENSION_SUFFIXES[0]
        ext_file = mod_dir / f"ext_mod{ext_suffix}"
        ext_file.write_text("")

        config = Config()
        finder = PathFinder(config, path=str(tmp_path))
        finder.paths = [str(mod_dir)]
        finder.stdlib_lib_prefix = "nonexistent"
        finder.conda_env = ""

        assert finder.find("ext_mod") == config.default_section

        # 2. __init__.py package match
        pkg_dir = mod_dir / "mypkg"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("")
        
        assert finder.find("mypkg") == config.default_section
    finally:
        tmp_dir.cleanup()
