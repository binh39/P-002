# file: src\sample_repo\isort\isort\deprecated\finders.py:167-199
# asked: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 196, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 196], [195, 198]]}
# gained: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 187, 189, 191, 192, 195, 198], "branches": [[168, 169], [180, 181], [181, 187], [187, 189], [189, 191], [191, 192], [191, 195], [192, 191], [195, 198]]}

import importlib.machinery
import os
from pathlib import Path
from isort import sections
from isort.deprecated.finders import PathFinder
from isort.settings import Config




def test_path_finder_virtual_env_src():
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        venv_dir = tmp_path / "venv"
        venv_dir.mkdir()
        src_inside_venv = venv_dir / "src"
        src_inside_venv.mkdir(parents=True)
        
        mod = src_inside_venv / "foo_venv.py"
        mod.write_text("# module")

        config = Config()
        finder = PathFinder(config, path=str(tmp_path))
        resolved_src_inside_venv = str(src_inside_venv.resolve())
        finder.paths = [resolved_src_inside_venv]
        finder.virtual_env = str(venv_dir.resolve())
        finder.virtual_env_src = resolved_src_inside_venv + "/"
        finder.stdlib_lib_prefix = "NONEXISTENT_STDLIB_PREFIX"
        finder.conda_env = ""

        assert finder.find("foo_venv") == sections.THIRDPARTY


def test_path_finder_extension_suffix_and_package():
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        ext_dir = tmp_path / "ext_dir"
        ext_dir.mkdir()
        
        if importlib.machinery.EXTENSION_SUFFIXES:
            suffix = importlib.machinery.EXTENSION_SUFFIXES[0]
            ext_mod = ext_dir / f"ext_mod{suffix}"
            ext_mod.write_text("")

        pkg_dir = ext_dir / "pkg_dir"
        pkg_dir.mkdir()
        init_file = pkg_dir / "__init__.py"
        init_file.write_text("")

        config = Config()
        finder = PathFinder(config, path=str(tmp_path))
        finder.paths = [str(ext_dir.resolve())]
        finder.stdlib_lib_prefix = "NONEXISTENT_STDLIB_PREFIX"
        finder.conda_env = ""
        finder.virtual_env = None

        if importlib.machinery.EXTENSION_SUFFIXES:
            assert finder.find("ext_mod") == config.default_section
        
        assert finder.find("pkg_dir") == config.default_section


def os_normcase(path):
    import os
    return os.path.normcase(path)
